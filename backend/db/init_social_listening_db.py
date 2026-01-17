"""
Initialize Social Listening database tables
Run this script to create the social listening tables in the database
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.db.database import engine, Base
from backend.db.models import (
    TrackingRule, FetchedPost, MatchedResult, 
    SentimentAnalysis, SocialAlert, MonitoringReport
)


async def init_db():
    """Create all social listening tables"""
    print("[DB] Initializing Social Listening tables...")
    
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
            print("[DB] ✅ Social Listening tables created successfully!")
            
            # List the tables that were created
            tables = [
                "tracking_rules",
                "fetched_posts", 
                "matched_results",
                "sentiment_analysis",
                "social_alerts",
                "monitoring_reports"
            ]
            print("[DB] Tables initialized:")
            for table in tables:
                print(f"    - {table}")
                
    except Exception as e:
        print(f"[DB] ❌ Error creating tables: {e}")
        raise


if __name__ == "__main__":
    print("=" * 50)
    print("Social Listening Database Initialization")
    print("=" * 50)
    asyncio.run(init_db())
    print("=" * 50)
    print("Done!")
