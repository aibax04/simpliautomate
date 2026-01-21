"""
Migration script to add high-accuracy timestamp extraction columns.
Adds timestamp_source and confidence_level to fetched_posts and matched_results.
"""
import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal

async def migrate():
    """Add timestamp metadata columns"""
    async with AsyncSessionLocal() as session:
        try:
            # Table: fetched_posts
            await session.execute(text("""
                ALTER TABLE fetched_posts 
                ADD COLUMN IF NOT EXISTS timestamp_source VARCHAR,
                ADD COLUMN IF NOT EXISTS confidence_level VARCHAR
            """))
            
            # Table: matched_results
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS timestamp_source VARCHAR,
                ADD COLUMN IF NOT EXISTS confidence_level VARCHAR
            """))
            
            await session.commit()
            print("[Migration] Successfully added timestamp extraction columns")
            
        except Exception as e:
            await session.rollback()
            print(f"[Migration] Error adding timestamp columns: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
