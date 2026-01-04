import asyncio
from sqlalchemy import text
from backend.db.database import engine, Base
from backend.db.models import ScheduledPost

async def init_db():
    print("[DB] Initializing Scheduler table...")
    async with engine.begin() as conn:
        print("[DB] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] Scheduler table initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
