import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import libsql_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_url = os.getenv("https://lifeflow-db-iniya.aws-ap-south-1.turso.io")
db_token = os.getenv("eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODI5MDQ4NTgsImlkIjoiMDE5ZjFkNjYtYzAwMS03MzNhLTkzNzktYjkzOGUwZTQwNzYzIiwia2lkIjoicGpjZDA5ZEVhUUZjQlBLZmlTclRTb3ZVTlk4MkV5ZlVJTmNELXp4OVZTVSIsInJpZCI6Ijk1ZjQ5Zjg2LWNmYTEtNGE2My04NDJiLTVhMGVlYjQ2YTk2ZiJ9.7KX2x74Y5ZFJQJF47wUB8eL90HaDRrmuRBAEv-Q926xYFyzpsGyqRUfSDbRePJShggjzlVfCltAtcC_4GYXsDw")

class AuthRequest(BaseModel):
    email: str
    username: str = ""
    isLogin: bool

@app.post("/auth")
async def authenticate_user(req: AuthRequest):
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        if not req.isLogin:
            user_id = f"usr_{os.urandom(4).hex()}"
            try:
                await client.execute(
                    "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
                    [user_id, req.email, req.username]
                )
                return {"status": "success", "user_id": user_id, "name": req.username, "role": "New User"}
            except Exception:
                raise HTTPException(status_code=400, detail="Email already exists.")
        else:
            result = await client.execute("SELECT id, name, role FROM users WHERE email = ?", [req.email])
            if len(result.rows) > 0:
                user = result.rows[0]
                return {"status": "success", "user_id": user[0], "name": user[1], "role": user[2]}
            else:
                raise HTTPException(status_code=404, detail="User not found.")

class TaskCreate(BaseModel):
    title: str
    date: str
    time: str = "12:00"
    priority: str = "medium"
    category: str = "Inbox"

class TaskUpdate(BaseModel):
    completed: bool

class HabitCreate(BaseModel):
    name: str
    category: str
    targetTime: str

class GoalCreate(BaseModel):
    title: str
    category: str
    targetDate: str

class MilestoneCreate(BaseModel):
    text: str
    date: str

# --- TASKS ---
@app.get("/tasks/{user_id}")
async def get_user_tasks(user_id: str):
    try:
        async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
            result = await client.execute("SELECT id, title, date, time, priority, category, completed FROM tasks WHERE user_id = ?", [user_id])
            tasks = [{"id": r[0], "title": r[1], "date": r[2], "time": r[3], "priority": r[4], "category": r[5], "completed": bool(r[6])} for r in result.rows]
            return {"tasks": tasks}
    except Exception:
        return {"tasks": []}

@app.post("/tasks/{user_id}")
async def create_task(user_id: str, task: TaskCreate):
    task_id = f"tsk_{uuid.uuid4().hex[:8]}"
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute(
            "INSERT INTO tasks (id, user_id, title, date, time, priority, category, completed) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            [task_id, user_id, task.title, task.date, task.time, task.priority, task.category]
        )
        return {"status": "success", "task_id": task_id}

@app.put("/tasks/{task_id}")
async def update_task_status(task_id: str, task_update: TaskUpdate):
    completed_int = 1 if task_update.completed else 0
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute("UPDATE tasks SET completed = ? WHERE id = ?", [completed_int, task_id])
        return {"status": "success"}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute("DELETE FROM tasks WHERE id = ?", [task_id])
        return {"status": "success"}

# --- HABITS ---
@app.get("/habits/{user_id}")
async def get_user_habits(user_id: str):
    try:
        async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
            habits_result = await client.execute("SELECT id, name, category, target_time, missed_streak FROM habits WHERE user_id = ?", [user_id])
            habits = []
            for row in habits_result.rows:
                habit_id = row[0]
                logs_result = await client.execute("SELECT date FROM habit_logs WHERE habit_id = ?", [habit_id])
                habits.append({
                    "id": habit_id, "name": row[1], "category": row[2], 
                    "targetTime": row[3], "missedStreak": bool(row[4]),
                    "completedDates": [log[0] for log in logs_result.rows]
                })
            return {"habits": habits}
    except Exception as e:
        return {"habits": []}

@app.post("/habits/{user_id}")
async def create_habit(user_id: str, habit: HabitCreate):
    habit_id = f"hbt_{uuid.uuid4().hex[:8]}"
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute(
            "INSERT INTO habits (id, user_id, name, category, target_time) VALUES (?, ?, ?, ?, ?)",
            [habit_id, user_id, habit.name, habit.category, habit.targetTime]
        )
        return {"status": "success", "habit_id": habit_id}

@app.post("/habits/{habit_id}/toggle")
async def toggle_habit_log(habit_id: str, date: str):
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        check = await client.execute("SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?", [habit_id, date])
        if len(check.rows) > 0:
            await client.execute("DELETE FROM habit_logs WHERE habit_id = ? AND date = ?", [habit_id, date])
            return {"status": "success", "action": "unlogged"}
        else:
            await client.execute("INSERT INTO habit_logs (habit_id, date) VALUES (?, ?)", [habit_id, date])
            return {"status": "success", "action": "logged"}

# --- GOALS ---
@app.get("/goals/{user_id}")
async def get_user_goals(user_id: str):
    try:
        async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
            goals_result = await client.execute("SELECT id, title, category, target_date, progress FROM goals WHERE user_id = ?", [user_id])
            goals = []
            for row in goals_result.rows:
                goal_id = row[0]
                miles_result = await client.execute("SELECT id, text, date, completed FROM milestones WHERE goal_id = ?", [goal_id])
                goals.append({
                    "id": goal_id, "title": row[1], "category": row[2],
                    "targetDate": row[3], "progress": row[4], 
                    "milestones": [{"id": m[0], "text": m[1], "date": m[2], "completed": bool(m[3])} for m in miles_result.rows]
                })
            return {"goals": goals}
    except Exception:
        return {"goals": []}

@app.post("/goals/{user_id}")
async def create_goal(user_id: str, goal: GoalCreate):
    goal_id = f"gol_{uuid.uuid4().hex[:8]}"
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute(
            "INSERT INTO goals (id, user_id, title, category, target_date) VALUES (?, ?, ?, ?, ?)",
            [goal_id, user_id, goal.title, goal.category, goal.targetDate]
        )
        return {"status": "success", "goal_id": goal_id}

@app.post("/goals/{goal_id}/milestones")
async def create_milestone(goal_id: str, milestone: MilestoneCreate):
    milestone_id = f"mil_{uuid.uuid4().hex[:8]}"
    async with libsql_client.create_client(url=db_url, auth_token=db_token) as client:
        await client.execute(
            "INSERT INTO milestones (id, goal_id, text, date) VALUES (?, ?, ?, ?)",
            [milestone_id, goal_id, milestone.text, milestone.date]
        )
        return {"status": "success", "milestone_id": milestone_id}