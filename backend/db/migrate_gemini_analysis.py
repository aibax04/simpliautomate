"""
Migration script to add Gemini analysis columns to matched_results table
Run this script to add sentiment, relevance, and keyword matching fields
"""
import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal

async def migrate():
    """Add Gemini analysis columns to matched_results table"""
    async with AsyncSessionLocal() as session:
        try:
            # Add sentiment column
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS sentiment VARCHAR DEFAULT 'neutral'
            """))
            
            # Add sentiment_score column
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0.5
            """))
            
            # Add relevance_score column
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS relevance_score FLOAT DEFAULT 0.5
            """))
            
            # Add matched_keywords column (JSONB)
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS matched_keywords JSONB DEFAULT '[]'::jsonb
            """))
            
            # Add explanation column
            await session.execute(text("""
                ALTER TABLE matched_results 
                ADD COLUMN IF NOT EXISTS explanation VARCHAR
            """))
            
            await session.commit()
            print("[Migration] Successfully added Gemini analysis columns to matched_results table")
            
        except Exception as e:
            await session.rollback()
            print(f"[Migration] Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
