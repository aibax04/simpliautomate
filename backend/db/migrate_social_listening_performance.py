
import asyncio
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from backend.db.database import engine

async def migrate():
    print("Starting migration: Adding missing indexes for Social Listening performance...")
    
    async with engine.begin() as conn:
        # MatchedResult
        print("Checking/Adding indexes to matched_results...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_user_id ON matched_results(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_post_id ON matched_results(post_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_rule_id ON matched_results(rule_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_important ON matched_results(important) WHERE important = true"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_saved ON matched_results(saved) WHERE saved = true"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matched_results_created_at ON matched_results(created_at)"))

        # TrackingRule
        print("Checking/Adding indexes to tracking_rules...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_rules_user_id ON tracking_rules(user_id)"))
        
        # FetchedPost
        print("Checking/Adding indexes to fetched_posts...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fetched_posts_posted_at ON fetched_posts(posted_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fetched_posts_platform ON fetched_posts(platform)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fetched_posts_external_id ON fetched_posts(external_id)"))

        # SocialAlert
        print("Checking/Adding indexes to social_alerts...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_alerts_user_id ON social_alerts(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_alerts_rule_id ON social_alerts(rule_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_alerts_post_id ON social_alerts(post_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_alerts_read ON social_alerts(read) WHERE read = false"))

    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
