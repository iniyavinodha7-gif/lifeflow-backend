import os
import asyncio
import libsql_client
from dotenv import load_dotenv

load_dotenv()

async def setup():
    url = os.getenv("https://lifeflow-db-iniya.aws-ap-south-1.turso.io")
    auth_token = os.getenv("eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODI5MDQ4NTgsImlkIjoiMDE5ZjFkNjYtYzAwMS03MzNhLTkzNzktYjkzOGUwZTQwNzYzIiwia2lkIjoicGpjZDA5ZEVhUUZjQlBLZmlTclRTb3ZVTlk4MkV5ZlVJTmNELXp4OVZTVSIsInJpZCI6Ijk1ZjQ5Zjg2LWNmYTEtNGE2My04NDJiLTVhMGVlYjQ2YTk2ZiJ9.7KX2x74Y5ZFJQJF47wUB8eL90HaDRrmuRBAEv-Q926xYFyzpsGyqRUfSDbRePJShggjzlVfCltAtcC_4GYXsDw")
    
    async with libsql_client.create_client(url=url, auth_token=auth_token) as client:
        # Users & Tasks 
        await client.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT,
          role TEXT DEFAULT 'Standard', created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        await client.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, date TEXT NOT NULL, time TEXT, priority TEXT DEFAULT 'medium',
          category TEXT DEFAULT 'Inbox', completed INTEGER DEFAULT 0
        );
        """)
        
        # Habits & Logs
        await client.execute("""
        CREATE TABLE IF NOT EXISTS habits (
          id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL, category TEXT, target_time TEXT, missed_streak INTEGER DEFAULT 0
        );
        """)

        await client.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
          habit_id TEXT REFERENCES habits(id) ON DELETE CASCADE,
          date TEXT NOT NULL,
          PRIMARY KEY (habit_id, date)
        );
        """)

        # Goals & Milestones
        await client.execute("""
        CREATE TABLE IF NOT EXISTS goals (
          id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, category TEXT, target_date TEXT, progress INTEGER DEFAULT 0
        );
        """)

        await client.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
          id TEXT PRIMARY KEY, goal_id TEXT REFERENCES goals(id) ON DELETE CASCADE,
          text TEXT NOT NULL, date TEXT NOT NULL, completed INTEGER DEFAULT 0
        );
        """)
        
    print("Database tables updated successfully.")

if __name__ == "__main__":
    asyncio.run(setup())