"""
Migration to add content field to MonitoringReport table
"""

import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal, engine


async def add_content_field():
    """Add content column to monitoring_reports table"""

    async with engine.begin() as conn:
        # Add the content column
        await conn.execute(text("""
            ALTER TABLE monitoring_reports
            ADD COLUMN IF NOT EXISTS content TEXT
        """))

        print("✅ Added content column to monitoring_reports table")


async def main():
    """Run the migration"""
    print("🔄 Running migration: Add content to monitoring_reports table")

    try:
        await add_content_field()
        print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())