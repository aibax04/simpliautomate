"""
Migration script to add cascade delete relationships
This will drop and recreate the social listening tables with proper cascade delete
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text


async def migrate_cascade():
    """Drop and recreate social listening tables with cascade delete"""
    from backend.db.database import engine
    from backend.db.models import (
        TrackingRule, FetchedPost, MatchedResult,
        SentimentAnalysis, SocialAlert, MonitoringReport
    )

    print("[Migration] Starting cascade delete migration...")

    # Tables to recreate (in order due to foreign keys)
    tables_to_drop = [
        "monitoring_reports",
        "social_alerts",
        "sentiment_analysis",
        "matched_results",
        "fetched_posts",
        "tracking_rules"
    ]

    async with engine.begin() as conn:
        # Drop existing tables if they exist
        for table in tables_to_drop:
            try:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"[Migration] Dropped table: {table}")
            except Exception as e:
                print(f"[Migration] Could not drop {table}: {e}")

        # Recreate all tables with cascade delete relationships
        from sqlalchemy import create_engine, MetaData
        from backend.db.database import Base

        # Create tables with the new relationships
        await conn.run_sync(Base.metadata.create_all)
        print("[Migration] SUCCESS - All tables recreated with cascade delete relationships")

    print("[Migration] Migration complete!")


if __name__ == "__main__":
    print("=" * 70)
    print("Social Listening Cascade Delete Migration")
    print("WARNING: This will DROP and RECREATE social listening tables!")
    print("All existing data will be lost!")
    print("=" * 70)

    asyncio.run(migrate_cascade())

    print("=" * 70)
    print("Done! Restart your server.")
