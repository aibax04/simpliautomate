"""
Migration to add database indexes for Live Feed filtering performance
"""

import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal, engine


async def add_filtering_indexes():
    """Add indexes for efficient feed filtering and sorting"""

    async with engine.begin() as conn:
        try:
            # Index on FetchedPost.posted_at for time range filtering
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fetched_post_posted_at
                ON fetched_posts (posted_at);
            """))

            # Index on FetchedPost.platform for platform filtering
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fetched_post_platform
                ON fetched_posts (platform);
            """))

            # Index on MatchedResult.rule_id for rule filtering
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_result_rule_id
                ON matched_results (rule_id);
            """))

            # Index on MatchedResult.user_id for user-specific queries
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_result_user_id
                ON matched_results (user_id);
            """))

            # Composite index for common filtering combination
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fetched_post_platform_posted_at
                ON fetched_posts (platform, posted_at);
            """))

            # Composite index for sorting optimization
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_result_user_created
                ON matched_results (user_id, created_at DESC);
            """))

            print("✅ Successfully added database indexes for feed filtering performance")

        except Exception as e:
            print(f"❌ Failed to add indexes: {e}")
            raise


async def main():
    """Run the migration"""
    print("🔄 Running migration: Add filtering indexes for Live Feed performance")

    try:
        await add_filtering_indexes()
        print("✅ Migration completed successfully!")
        print("\n📊 Added indexes:")
        print("  • idx_fetched_post_posted_at - Time range filtering")
        print("  • idx_fetched_post_platform - Platform filtering")
        print("  • idx_matched_result_rule_id - Rule filtering")
        print("  • idx_matched_result_user_id - User-specific queries")
        print("  • idx_fetched_post_platform_posted_at - Combined filtering")
        print("  • idx_matched_result_user_created - Sorting optimization")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())