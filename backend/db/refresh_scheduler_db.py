import asyncio
from sqlalchemy import text
from backend.db.database import engine, Base
from backend.db.models import ScheduledPost

async def init_db():
    print("[DB] Refreshing ScheduledPost table...")
    async with engine.begin() as conn:
        # Check if table exists, if so drop it to recreate with new column
        # Alternatively, just add the column. But dropping/recreating is cleaner for dev.
        await conn.execute(text("DROP TABLE IF EXISTS scheduled_posts CASCADE"))
        print("[DB] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] ScheduledPost table refreshed successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
