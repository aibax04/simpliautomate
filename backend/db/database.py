import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Single source of truth for DATABASE_URL
_db_url = os.getenv("DATABASE_URL")

if _db_url:
    # Render provides postgres:// but asyncpg needs postgresql+asyncpg://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _db_url.startswith("postgresql://") and "asyncpg" not in _db_url:
        _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    DATABASE_URL = _db_url
else:
    # Local development fallback
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/simplii"

print(f"[DB] Initializing engine with URL (masked): {DATABASE_URL.split('@')[-1]}")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

from sqlalchemy import text

async def check_db_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("[DB] Connection successful.")
    except Exception as e:
        print(f"[DB ERROR] Connection failed: {e}")
