import asyncio
import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.db.database import engine, check_db_connection
from backend.db.models import Base

async def test_db():
    print("--- Database Diagnostics ---")
    load_dotenv()
    
    # 1. Check connection
    print(f"Connecting to: {os.getenv('DATABASE_URL')}")
    await check_db_connection()
    
    # 2. Try to sync models (create tables if they don't exist)
    try:
        async with engine.begin() as conn:
            print("Checking/Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
        print("[Success] Tables are synchronized.")
    except Exception as e:
        print(f"[Error] Table sync failed: {e}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_db())
