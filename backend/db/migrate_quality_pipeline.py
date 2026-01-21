
import asyncio
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from backend.db.database import engine

async def migrate():
    print("Starting migration: Enhancing quality and source metadata...")
    
    async with engine.begin() as conn:
        # Check existing columns for fetched_posts
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'fetched_posts'"))
        existing_fetched_columns = [row[0] for row in result.all()]
        
        fetched_columns_to_add = [
            ("source_type", "VARCHAR"),
            ("credibility_score", "FLOAT DEFAULT 0.0"),
            ("content_hash", "VARCHAR")
        ]
        
        for col_name, col_type in fetched_columns_to_add:
            if col_name not in existing_fetched_columns:
                print(f"Adding column to fetched_posts: {col_name}")
                await conn.execute(text(f"ALTER TABLE fetched_posts ADD COLUMN {col_name} {col_type}"))
        
        # Check existing columns for matched_results
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'matched_results'"))
        existing_matched_columns = [row[0] for row in result.all()]
        
        matched_columns_to_add = [
            ("relevance_score", "FLOAT DEFAULT 0.0"),
            ("source_credibility", "FLOAT DEFAULT 0.0"),
            ("matched_keywords", "JSON"),
            ("match_explanation", "TEXT")
        ]
        
        for col_name, col_type in matched_columns_to_add:
            if col_name not in existing_matched_columns:
                print(f"Adding column to matched_results: {col_name}")
                await conn.execute(text(f"ALTER TABLE matched_results ADD COLUMN {col_name} {col_type}"))
                
        # Add indexes
        print("Adding content_hash index...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fetched_posts_content_hash ON fetched_posts(content_hash)"))
            
    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
