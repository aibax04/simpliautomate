import asyncio
from sqlalchemy import text
from backend.db.database import engine, Base
from backend.db.models import LinkedInAccount

async def init_db():
    print("[DB] Initializing LinkedIn accounts table...")
    async with engine.begin() as conn:
        print("[DB] Dropping existing linkedin_accounts table if exists...")
        await conn.execute(text("DROP TABLE IF EXISTS linkedin_accounts CASCADE"))
        
        print("[DB] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] LinkedIn accounts table initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
