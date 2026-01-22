"""
Migration to add performance indexes for Live Feed API optimization
Ensures <500ms response times for feed queries with pagination and filtering
"""

import asyncio
from sqlalchemy import text
from backend.db.database import AsyncSessionLocal, engine


async def add_performance_indexes():
    """Add indexes for optimal Live Feed API performance"""

    async with engine.begin() as conn:
        try:
            # Core indexes for MatchedResult table (main feed table)
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_user_id_created_at
                ON matched_results (user_id, created_at DESC);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_posted_at_desc
                ON matched_results (posted_at DESC);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_rule_id
                ON matched_results (rule_id);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_platform
                ON matched_results (platform);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_sentiment
                ON matched_results (sentiment);
            """))

            # Composite indexes for common filtering combinations
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_user_platform_posted_at
                ON matched_results (user_id, platform, posted_at DESC);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_matched_results_user_rule_posted_at
                ON matched_results (user_id, rule_id, posted_at DESC);
            """))

            # FetchedPost indexes for join optimization
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fetched_posts_posted_at
                ON fetched_posts (posted_at DESC);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fetched_posts_platform
                ON fetched_posts (platform);
            """))

            # TrackingRule indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tracking_rules_user_id_status
                ON tracking_rules (user_id, status);
            """))

            print("SUCCESS: Successfully added performance indexes for Live Feed API")

        except Exception as e:
            print(f"ERROR: Failed to add performance indexes: {e}")
            raise


async def create_optimized_feed_view():
    """Create a materialized view for faster feed queries (optional optimization)"""

    async with engine.begin() as conn:
        try:
            # Drop existing view if it exists
            await conn.execute(text("""
                DROP MATERIALIZED VIEW IF EXISTS feed_optimized_view;
            """))

            # Create optimized view for feed queries
            await conn.execute(text("""
                CREATE MATERIALIZED VIEW feed_optimized_view AS
                SELECT
                    mr.id,
                    mr.user_id,
                    mr.post_id,
                    mr.rule_id,
                    mr.sentiment,
                    mr.sentiment_score,
                    mr.relevance_score,
                    mr.matched_keywords,
                    mr.important,
                    mr.saved,
                    mr.created_at,
                    mr.posted_at,
                    fp.platform,
                    fp.author,
                    fp.handle,
                    fp.content,
                    fp.url,
                    fp.quality_score,
                    tr.name as rule_name
                FROM matched_results mr
                LEFT JOIN fetched_posts fp ON mr.post_id = fp.id
                LEFT JOIN tracking_rules tr ON mr.rule_id = tr.id
                WHERE mr.posted_at IS NOT NULL
                ORDER BY mr.posted_at DESC;
            """))

            # Create indexes on the materialized view
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_feed_view_user_posted_at
                ON feed_optimized_view (user_id, posted_at DESC);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_feed_view_user_platform
                ON feed_optimized_view (user_id, platform);
            """))

            print("SUCCESS: Created optimized feed materialized view")

        except Exception as e:
            print(f"WARN: Could not create materialized view (optional): {e}")


async def analyze_table_statistics():
    """Update table statistics for query planner optimization"""

    async with engine.begin() as conn:
        try:
            # Analyze tables for better query planning
            await conn.execute(text("ANALYZE matched_results;"))
            await conn.execute(text("ANALYZE fetched_posts;"))
            await conn.execute(text("ANALYZE tracking_rules;"))

            print("SUCCESS: Updated table statistics for query optimization")

        except Exception as e:
            print(f"WARN: Could not analyze tables: {e}")


async def main():
    """Run the performance optimization migration"""
    print("RUNNING: Add performance indexes for Live Feed API")
    print("=" * 60)

    try:
        print("Adding database indexes...")
        await add_performance_indexes()

        print("Creating optimized view...")
        await create_optimized_feed_view()

        print("Analyzing table statistics...")
        await analyze_table_statistics()

        print("\nSUCCESS: Migration completed successfully!")
        print("\nAdded indexes:")
        print("  - idx_matched_results_user_id_created_at - Pagination and user queries")
        print("  - idx_matched_results_posted_at_desc - Sorting by posted date")
        print("  - idx_matched_results_rule_id - Rule filtering")
        print("  - idx_matched_results_platform - Platform filtering")
        print("  - idx_matched_results_sentiment - Sentiment filtering")
        print("  - idx_matched_results_user_platform_posted_at - Combined filtering")
        print("  - idx_matched_results_user_rule_posted_at - Rule + time filtering")
        print("  - idx_fetched_posts_posted_at - Join optimization")
        print("  - idx_fetched_posts_platform - Join optimization")
        print("  - idx_tracking_rules_user_id_status - Rule queries")
        print("\nLive Feed API should now respond in under 500ms!")

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())