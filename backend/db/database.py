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
    print(f"[DB] Using environment DATABASE_URL (host: {DATABASE_URL.split('@')[-1].split('/')[0]})")
else:
    # Check if we are on Render
    if os.getenv("RENDER"):
        print("❌ CRITICAL ERROR: DATABASE_URL environment variable is NOT SET on Render!")
        # We don't crash here to allow the health check to potentially report status
        DATABASE_URL = "postgresql+asyncpg://missing_url_on_render"
    else:
        # Local development fallback
        DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/simplii"
        print("[DB] Using local development database.")

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
