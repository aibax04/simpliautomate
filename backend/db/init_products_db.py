import asyncio
from sqlalchemy import text
from backend.db.database import engine, Base
from backend.db.models import Product

async def init_db():
    print("[DB] Initializing Products table...")
    async with engine.begin() as conn:
        print("[DB] Creating all tables (including products)...")
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] Products table initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
