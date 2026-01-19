"""
Migration to add notification_email field to User table
"""

import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal, engine


async def add_notification_email_field():
    """Add notification_email column to users table"""

    async with engine.begin() as conn:
        # Add the notification_email column
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS notification_email VARCHAR(255)
        """))

        print("✅ Added notification_email column to users table")


async def main():
    """Run the migration"""
    print("🔄 Running migration: Add notification_email to users table")

    try:
        await add_notification_email_field()
        print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())