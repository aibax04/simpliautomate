"""
Migration to add filter_has_contact_email to TrackingRule (tracking_rules table)
"""

import asyncio
from sqlalchemy import text
from backend.db.database import engine


async def add_filter_has_contact_email():
    """Add filter_has_contact_email column to tracking_rules table"""

    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE tracking_rules
            ADD COLUMN IF NOT EXISTS filter_has_contact_email BOOLEAN DEFAULT FALSE
        """))
        print("Added filter_has_contact_email column to tracking_rules table")


async def main():
    print("Running migration: Add filter_has_contact_email to tracking_rules")
    try:
        await add_filter_has_contact_email()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
