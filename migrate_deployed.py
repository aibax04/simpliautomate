import asyncio
from sqlalchemy import text
import sys
import os

# Add the project root to the python path so we can import backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.db.database import AsyncSessionLocal

async def migrate():
    print("🚀 Connecting to database to add missing columns...")
    async with AsyncSessionLocal() as session:
        try:
            # 1. Add last_image_edit_prompt
            print("Checking/Adding 'last_image_edit_prompt' column...")
            await session.execute(text(
                "ALTER TABLE generated_posts ADD COLUMN IF NOT EXISTS last_image_edit_prompt VARCHAR;"
            ))
            
            # 2. Add image_updated_at
            print("Checking/Adding 'image_updated_at' column...")
            await session.execute(text(
                "ALTER TABLE generated_posts ADD COLUMN IF NOT EXISTS image_updated_at TIMESTAMP WITH TIME ZONE;"
            ))
            
            await session.commit()
            print("✅ Database schema updated successfully!")
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
