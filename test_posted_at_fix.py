#!/usr/bin/env python3
"""
Test script to verify the posted_at attribute fix
"""

import asyncio
from sqlalchemy import select
from backend.db.database import AsyncSessionLocal
from backend.db.models import MatchedResult, FetchedPost, TrackingRule

async def test_query():
    """Test that the query works with posted_at from FetchedPost"""

    async with AsyncSessionLocal() as session:
        try:
            # Test the query structure we use in the API
            stmt = select(
                MatchedResult.id,
                MatchedResult.post_id,
                MatchedResult.rule_id,
                FetchedPost.posted_at,  # This should work now
                FetchedPost.platform,
                TrackingRule.name.label("rule_name")
            ).select_from(
                MatchedResult
            ).outerjoin(
                FetchedPost, MatchedResult.post_id == FetchedPost.id
            ).outerjoin(
                TrackingRule, MatchedResult.rule_id == TrackingRule.id
            ).limit(1)

            result = await session.execute(stmt)
            row = result.first()

            if row:
                print("SUCCESS: Query executed successfully")
                print(f"Row data: id={row.id}, posted_at={row.posted_at}, platform={row.platform}")
                return True
            else:
                print("WARNING: No data found in database, but query structure is correct")
                return True

        except Exception as e:
            print(f"ERROR: Query failed with: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(test_query())
    if result:
        print("\n✅ posted_at attribute issue has been FIXED!")
    else:
        print("\n❌ posted_at attribute issue still exists!")