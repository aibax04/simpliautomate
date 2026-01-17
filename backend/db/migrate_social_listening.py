"""
Migration script to fix Social Listening tables
This will drop and recreate the tables with the correct schema
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text


async def migrate():
    """Drop and recreate social listening tables"""
    from backend.db.database import engine, Base
    from backend.db.models import (
        TrackingRule, FetchedPost, MatchedResult, 
        SentimentAnalysis, SocialAlert, MonitoringReport
    )
    
    print("[Migration] Starting Social Listening table migration...")
    
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
        
        # Recreate all tables with correct schema
        await conn.run_sync(Base.metadata.create_all)
        print("[Migration] SUCCESS - All tables recreated with correct schema!")
    
    print("[Migration] Migration complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("Social Listening Database Migration")
    print("WARNING: This will DROP and RECREATE social listening tables!")
    print("=" * 60)
    
    asyncio.run(migrate())
    
    print("=" * 60)
    print("Done! Restart your server.")
