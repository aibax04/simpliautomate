import asyncio
from sqlalchemy import text
from backend.db.database import engine

async def migrate():
    print("Migrating tracking_rules table...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE tracking_rules ADD COLUMN last_run_at TIMESTAMPTZ;"))
            print("Successfully added last_run_at column.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column last_run_at already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
