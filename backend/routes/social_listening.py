"""
Social Listening API Routes
Handles tracking rules, feed, alerts, analytics, and AI response generation
"""

# IMPORTS
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_, text
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import time

from backend.db.database import get_db
from backend.db.models import (
    User, TrackingRule, FetchedPost, MatchedResult, 
    SentimentAnalysis, SocialAlert, MonitoringReport
)
from backend.auth.security import get_current_user
from backend.config import Config
from backend.agents.social_listening_agent import get_social_listening_agent
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/social-listening", tags=["Social Listening"])


async def generate_report_content(db: AsyncSession, user_id: int, report_type: str,
                                start_date: datetime, end_date: datetime, rule_ids: List[str],
                                platform: str = "all", source: str = "all", min_relevance: int = 0):
    """Generate clean, readable report content with bullet points"""

    print(f"[Reports] Generating {report_type} report content for user {user_id}")
    report_lines = []

    # Report Header
    report_lines.append("SOCIAL MEDIA MONITORING REPORT")
    report_lines.append("=" * 50)
    report_lines.append("")

    # Report Info
    report_lines.append("REPORT DETAILS")
    report_lines.append("- Report Type: {}".format(report_type.title()))
    report_lines.append("- Date Range: {} to {}".format(
        start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    ))
    report_lines.append("- Filters: Platform={}, Source={}, Min Relevance={}".format(
        platform.title(), source.title(), min_relevance
    ))
    report_lines.append("- Generated: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    report_lines.append("")

    # Get data based on report type
    try:
        if report_type == "summary":
            print("[Reports] Generating summary report...")
            content = await generate_summary_report(db, user_id, start_date, end_date, rule_ids, platform, source, min_relevance)
        elif report_type == "detailed":
            print("[Reports] Generating detailed report...")
            content = await generate_detailed_report(db, user_id, start_date, end_date, rule_ids, platform, source, min_relevance)
        elif report_type == "sentiment":
            print("[Reports] Generating sentiment report...")
            content = await generate_sentiment_report(db, user_id, start_date, end_date, rule_ids, platform, source, min_relevance)
        elif report_type == "smart_analysis":
            print("[Reports] Generating smart analysis report...")
            content = await generate_smart_analysis_report(db, user_id, start_date, end_date, rule_ids, platform, source, min_relevance)
        else:
            print(f"[Reports] Invalid report type: {report_type}")
            content = ["- Invalid report type specified"]

        report_lines.extend(content)
        print(f"[Reports] Report content generated with {len(content)} lines")

    except Exception as e:
        print(f"[Reports] Error generating report content: {e}")
        import traceback
        traceback.print_exc()
        report_lines.extend([
            "",
            "ERROR GENERATING REPORT",
            "- An error occurred while generating this report",
            "- Please try again or contact support if the issue persists"
        ])

    return "\n".join(report_lines)




async def generate_summary_report(db: AsyncSession, user_id: int, start_date: datetime,
                                end_date: datetime, rule_ids: List[str],
                                platform: str = "all", source: str = "all", min_relevance: int = 0):
    """Generate summary report with key metrics"""

    print(f"[Reports] Generating summary report for date range: {start_date} to {end_date}")
    lines = []
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 20)

    try:
        # Base query for posts
        base_stmt = select(func.count(FetchedPost.id))
        
        # Apply joins if needed based on filters
        if rule_ids or min_relevance > 0 or source == "saved":
            base_stmt = base_stmt.join(MatchedResult, FetchedPost.id == MatchedResult.post_id)
        
        # Build conditions
        conditions = [
            FetchedPost.posted_at >= start_date,
            FetchedPost.posted_at <= end_date
        ]
        
        # Add user filter via MatchedResult if joined, or implicit via rule owner? 
        # Safest to check MatchedResult owner if we join it
        if rule_ids or min_relevance > 0 or source == "saved":
             conditions.append(MatchedResult.user_id == user_id)
        
        if platform and platform != "all":
            conditions.append(FetchedPost.platform == platform)
            
        if rule_ids:
             conditions.append(MatchedResult.rule_id.in_([int(rid) for rid in rule_ids]))
             
        if min_relevance > 0:
            conditions.append(MatchedResult.relevance_score >= min_relevance)
            
        if source == "saved":
            conditions.append(MatchedResult.saved == True)

        stmt = base_stmt.where(and_(*conditions))
        
        result = await db.execute(stmt)
        total_posts = result.scalar() or 0
        print(f"[Reports] Found {total_posts} total posts")
        lines.append("- Total Posts Monitored: {}".format(total_posts))

        # Get posts by platform (reuse conditions but group by)
        platform_stmt = select(
            FetchedPost.platform,
            func.count(FetchedPost.id).label('count')
        )
        
        if rule_ids or min_relevance > 0 or source == "saved":
            platform_stmt = platform_stmt.join(MatchedResult, FetchedPost.id == MatchedResult.post_id)
            
        platform_stmt = platform_stmt.where(and_(*conditions)).group_by(FetchedPost.platform)
        
        platform_result = await db.execute(platform_stmt)
        platform_counts = platform_result.all()

        print(f"[Reports] Found platform counts: {platform_counts}")

        if platform_counts:
            lines.append("- Posts by Platform:")
            for platform, count in platform_counts:
                lines.append("  - {}: {}".format(platform.title(), count))

        # Get alert count
        alert_stmt = select(func.count(SocialAlert.id)).where(
            and_(
                SocialAlert.user_id == user_id,
                SocialAlert.created_at >= start_date,
                SocialAlert.created_at <= end_date
            )
        )
        alert_result = await db.execute(alert_stmt)
        alert_count = alert_result.scalar() or 0
        print(f"[Reports] Found {alert_count} alerts")
        lines.append("- Alerts Triggered: {}".format(alert_count))

        # Get active rules
        rule_stmt = select(func.count(TrackingRule.id)).where(
            and_(
                TrackingRule.user_id == user_id,
                TrackingRule.status == "active"
            )
        )
        rule_result = await db.execute(rule_stmt)
        active_rules = rule_result.scalar() or 0
        print(f"[Reports] Found {active_rules} active rules")
        lines.append("- Active Tracking Rules: {}".format(active_rules))

        lines.append("")
        lines.append("KEY FINDINGS")
        lines.append("-" * 15)

        # Most active platforms
        if platform_counts:
            most_active = max(platform_counts, key=lambda x: x[1])
            lines.append("- Most Active Platform: {} ({} posts)".format(
                most_active[0].title(), most_active[1]))

        # Alert frequency
        if total_posts > 0:
            alert_rate = (alert_count / total_posts) * 100
            lines.append("- Alert Rate: {:.1f}% of monitored posts".format(alert_rate))
        else:
            lines.append("- No posts found in the selected date range")

        print(f"[Reports] Summary report generated with {len(lines)} lines")
        return lines

    except Exception as e:
        print(f"[Reports] Error in summary report generation: {e}")
        import traceback
        traceback.print_exc()
        return [
            "EXECUTIVE SUMMARY",
            "-" * 20,
            "- Error generating summary report",
            "- Please try again or contact support"
        ]


async def generate_detailed_report(db: AsyncSession, user_id: int, start_date: datetime,
                                 end_date: datetime, rule_ids: List[str],
                                 platform: str = "all", source: str = "all", min_relevance: int = 0):
    """Generate detailed report with post-by-post breakdown"""

    lines = []
    lines.append("DETAILED ANALYSIS")
    lines.append("-" * 20)

    # Get posts with their matching rules
    stmt = select(
        FetchedPost,
        MatchedResult.rule_id,
        TrackingRule.name.label('rule_name')
    ).join(
        MatchedResult, FetchedPost.id == MatchedResult.post_id
    ).join(
        TrackingRule, MatchedResult.rule_id == TrackingRule.id
    ).where(
        and_(
            FetchedPost.posted_at >= start_date,
            FetchedPost.posted_at <= end_date,
            TrackingRule.user_id == user_id
        )
    )

    # Apply filters
    if platform and platform != "all":
        stmt = stmt.where(FetchedPost.platform == platform)
    
    if rule_ids:
        stmt = stmt.where(TrackingRule.id.in_([int(rid) for rid in rule_ids]))

    if min_relevance > 0:
        stmt = stmt.where(MatchedResult.relevance_score >= min_relevance)

    if source == "saved":
        stmt = stmt.where(MatchedResult.saved == True)

    stmt = stmt.order_by(FetchedPost.created_at.desc()).limit(50)

    result = await db.execute(stmt)
    posts = result.all()

    if not posts:
        lines.append("- No posts found in the specified date range")
        return lines

    lines.append("- Recent Matched Posts (Last 50):")
    lines.append("")

    current_date = None
    for post, rule_id, rule_name in posts:
        post_date = post.created_at.date()

        # Group by date
        if post_date != current_date:
            if current_date is not None:
                lines.append("")
            lines.append("{}:".format(post_date.strftime("%Y-%m-%d")))
            current_date = post_date

        # Format post info
        author = post.author[:30] + "..." if len(post.author or "") > 30 else (post.author or "Unknown")
        content_preview = post.content[:80] + "..." if len(post.content or "") > 80 else (post.content or "")

        lines.append("  - [{}] {} | {} | {}".format(
            post.platform.upper(),
            author,
            rule_name,
            content_preview
        ))

    return lines


async def generate_sentiment_report(db: AsyncSession, user_id: int, start_date: datetime,
                                  end_date: datetime, rule_ids: List[str],
                                  platform: str = "all", source: str = "all", min_relevance: int = 0):
    """Generate sentiment-focused report"""

    lines = []
    lines.append("SENTIMENT ANALYSIS")
    lines.append("-" * 20)

    # Get sentiment data from the last 30 days of analysis
    sentiment_stmt = select(
        SentimentAnalysis.sentiment,
        func.count(SentimentAnalysis.id).label('count')
    ).join(
        FetchedPost, SentimentAnalysis.post_id == FetchedPost.id
    ).where(
        and_(
            FetchedPost.posted_at >= start_date,
            FetchedPost.posted_at <= end_date
        )
    )

    # Apply filters to sentiment analysis
    # We need to join with MatchedResult to filter by rule, relevance, etc.
    sentiment_stmt = sentiment_stmt.join(MatchedResult, FetchedPost.id == MatchedResult.post_id)
    
    if platform and platform != "all":
        sentiment_stmt = sentiment_stmt.where(FetchedPost.platform == platform)
        
    if rule_ids:
        sentiment_stmt = sentiment_stmt.where(MatchedResult.rule_id.in_([int(rid) for rid in rule_ids]))
        
    if min_relevance > 0:
        sentiment_stmt = sentiment_stmt.where(MatchedResult.relevance_score >= min_relevance)
        
    if source == "saved":
        sentiment_stmt = sentiment_stmt.where(MatchedResult.saved == True)

    sentiment_stmt = sentiment_stmt.group_by(SentimentAnalysis.sentiment)

    sentiment_result = await db.execute(sentiment_stmt)
    sentiment_data = sentiment_result.all()

    if sentiment_data:
        total = sum(count for _, count in sentiment_data)
        lines.append(f"- Total Posts Analyzed: {total}")
        lines.append("")
        lines.append("- Sentiment Distribution:")

        for sentiment, count in sentiment_data:
            percentage = (count / total) * 100
            sentiment_label = sentiment.title() if sentiment else "Neutral"
            lines.append("  - {}: {} posts ({:.1f}%)".format(sentiment_label, count, percentage))

        # Most common sentiment
        most_common = max(sentiment_data, key=lambda x: x[1])
        sentiment_name = most_common[0].title() if most_common[0] else "Neutral"
        lines.append("- Dominant Sentiment: {} ({} posts)".format(sentiment_name, most_common[1]))
    else:
        lines.append("- No sentiment analysis data available for the selected period")
        lines.append("- Enable sentiment analysis in your tracking rules to see this data")

    # Get top keywords by sentiment
    lines.append("")
    lines.append("TOP KEYWORDS BY SENTIMENT")
    lines.append("-" * 25)

    # This would require more complex analysis - for now, show placeholder
    lines.append("- Feature coming soon: Keyword sentiment analysis")

    return lines

    return lines


async def generate_smart_analysis_report(db: AsyncSession, user_id: int, start_date: datetime,
                                       end_date: datetime, rule_ids: List[str],
                                       platform: str = "all", source: str = "all", min_relevance: int = 0):
    """Generate smart analysis report using Gemini for trends, topic brief, and sentiment"""
    
    lines = []
    lines.append("SMART TREND & TOPIC ANALYSIS")
    lines.append("-" * 25)
    
    # Fetch posts to analyze
    stmt = select(
        FetchedPost.content,
        FetchedPost.platform,
        FetchedPost.posted_at,
        MatchedResult.sentiment,
        TrackingRule.name
    ).join(
        MatchedResult, FetchedPost.id == MatchedResult.post_id
    ).join(
        TrackingRule, MatchedResult.rule_id == TrackingRule.id
    ).where(
        and_(
            FetchedPost.posted_at >= start_date,
            FetchedPost.posted_at <= end_date,
            MatchedResult.user_id == user_id
        )
    )
    
    # Apply filters
    if platform and platform != "all":
        stmt = stmt.where(FetchedPost.platform == platform)
    if rule_ids:
        stmt = stmt.where(MatchedResult.rule_id.in_([int(rid) for rid in rule_ids]))
    if min_relevance > 0:
        stmt = stmt.where(MatchedResult.relevance_score >= min_relevance)
    if source == "saved":
        stmt = stmt.where(MatchedResult.saved == True)
        
    # Order by relevance and limit to top 30 for analysis context window
    stmt = stmt.order_by(MatchedResult.relevance_score.desc()).limit(30)
    
    result = await db.execute(stmt)
    posts = result.all()
    
    if not posts:
        lines.append("- No posts found matching criteria for analysis")
        return lines

    lines.append(f"- Total Posts Analyzed: {len(posts)}")
    lines.append("")
        
    # Prepare context for Gemini
    posts_context = "Social Media Posts:\n\n"
    for i, (content, plat, posted_at, sentiment, rule) in enumerate(posts):
        posts_context += f"{i+1}. [{plat} | {rule}] {content[:200]}... (Sentiment: {sentiment})\n"
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash") # Use 2.0 flash for speed and context
        
        prompt = f"""
        Analyze the following social media posts and provide a comprehensive report segment.
        
        Posts Data:
        {posts_context}
        
        Please provide the following sections with clear headers (no markdown bolding, just capitalized headers):
        
        1. TOPIC BRIEF
        A short brief (2-3 sentences) explaining what the main topics are reflecting in these posts.
        
        2. TREND ANALYSIS
        Where is the trend going? Is it increasing, decreasing, or shifting focus? What are the emerging angles?
        
        3. SENTIMENT INSIGHTS
        Where are the sentiments leaning? What is driving positive or negative sentiment?
        
        Format as plain text with bullet points (- ) for readability.
        """
        
        response = model.generate_content(prompt)
        analysis_text = response.text.strip()
        
        # Clean up markdown chars if any remain, though we asked for plain text
        analysis_text = analysis_text.replace("**", "").replace("##", "")
        
        lines.append(analysis_text)
        
    except Exception as e:
        print(f"[Reports] Error generating AI analysis: {e}")
        lines.append("- Error generating AI analysis. Please try again later.")
        lines.append(f"- Detail: {str(e)}")
        
    return lines
# ==================== Pydantic Models ====================

class RuleCreate(BaseModel):
    name: str
    keywords: List[str] = []
    handles: List[str] = []
    platforms: List[str] = []
    logic_type: str = "keywords_or_handles"
    frequency: str = "hourly"
    sentiment_filter: str = "all"  # all, positive, negative, neutral
    alert_email: bool = False
    alert_in_app: bool = True
    status: str = "active"


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    handles: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    logic_type: Optional[str] = None
    frequency: Optional[str] = None
    sentiment_filter: Optional[str] = None
    alert_email: Optional[bool] = None
    alert_in_app: Optional[bool] = None
    status: Optional[str] = None


class ResponseGenerateRequest(BaseModel):
    original_content: str
    platform: str
    intent: str = "professional"
    tone: str = "professional"
    length: str = "medium"


class ReportGenerateRequest(BaseModel):
    type: str
    start_date: str
    end_date: str
    rule_ids: List[str] = []
    platform: Optional[str] = "all"
    source: Optional[str] = "all"  # all, saved
    min_relevance: Optional[int] = 0


# ==================== Rules Endpoints ====================

@router.get("/rules")
async def get_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all tracking rules for the current user"""
    try:
        stmt = select(TrackingRule).where(
            TrackingRule.user_id == user.id
        ).order_by(desc(TrackingRule.created_at))
        
        result = await db.execute(stmt)
        rules = result.scalars().all()
        
        return {
            "rules": [
                {
                    "id": str(rule.id),
                    "name": rule.name,
                    "keywords": rule.keywords or [],
                    "handles": rule.handles or [],
                    "platforms": rule.platforms or [],
                    "logic_type": rule.logic_type,
                    "frequency": rule.frequency,
                    "sentiment_filter": getattr(rule, "sentiment_filter", "all"),
                    "alert_email": rule.alert_email,
                    "alert_in_app": rule.alert_in_app,
                    "status": rule.status,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None
                }
                for rule in rules
            ]
        }
    except Exception as e:
        print(f"[SocialListening] Error fetching rules: {e}")
        # Return empty list instead of crashing - tables may not exist yet
        return {"rules": []}


@router.post("/rules")
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a new tracking rule"""
    try:
        new_rule = TrackingRule(
            user_id=user.id,
            name=rule_data.name,
            keywords=rule_data.keywords,
            handles=rule_data.handles,
            platforms=rule_data.platforms,
            logic_type=rule_data.logic_type,
            frequency=rule_data.frequency,
            sentiment_filter=rule_data.sentiment_filter,
            alert_email=rule_data.alert_email,
            alert_in_app=rule_data.alert_in_app,
            status=rule_data.status
        )
        
        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)
        
        return {
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "keywords": new_rule.keywords or [],
                "handles": new_rule.handles or [],
                "platforms": new_rule.platforms or [],
                "logic_type": new_rule.logic_type,
                "frequency": new_rule.frequency,
                "alert_email": new_rule.alert_email,
                "alert_in_app": new_rule.alert_in_app,
                "status": new_rule.status,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None
            }
        }
    except Exception as e:
        await db.rollback()
        print(f"[SocialListening] Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update a tracking rule"""
    try:
        stmt = select(TrackingRule).where(
            TrackingRule.id == rule_id,
            TrackingRule.user_id == user.id
        )
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Update only provided fields
        update_data = rule_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(rule, field, value)
        
        await db.commit()
        await db.refresh(rule)
        
        return {"status": "success", "rule": {"id": str(rule.id), "status": rule.status}}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[SocialListening] Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Delete a tracking rule and all associated data"""
    try:
        # First, find the rule to ensure it exists and belongs to the user
        stmt = select(TrackingRule).where(
            TrackingRule.id == rule_id,
            TrackingRule.user_id == user.id
        )
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        # Delete all MatchedResult records for this rule
        from sqlalchemy import delete
        await db.execute(
            delete(MatchedResult).where(MatchedResult.rule_id == rule_id)
        )

        # Delete all SocialAlert records for this rule
        await db.execute(
            delete(SocialAlert).where(SocialAlert.rule_id == rule_id)
        )

        # Delete the rule itself
        await db.delete(rule)

        # Optional: Clean up orphaned FetchedPost records that are no longer referenced by any rules
        # Find posts that are only referenced by this deleted rule
        from sqlalchemy import exists
        orphaned_posts_stmt = select(FetchedPost.id).where(
            ~exists().where(MatchedResult.post_id == FetchedPost.id)
        )
        orphaned_posts = await db.execute(orphaned_posts_stmt)
        orphaned_post_ids = [row[0] for row in orphaned_posts.all()]

        if orphaned_post_ids:
            await db.execute(
                delete(FetchedPost).where(FetchedPost.id.in_(orphaned_post_ids))
            )
            print(f"[SocialListening] Cleaned up {len(orphaned_post_ids)} orphaned posts")

        await db.commit()

        return {"status": "success", "cleaned_up_posts": len(orphaned_post_ids) if 'orphaned_post_ids' in locals() else 0}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[SocialListening] Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Fetch/Refresh Endpoint ====================

@router.post("/fetch")
async def fetch_content(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Trigger background content fetching for all active rules.

    ⚠️  WARNING: This endpoint triggers synchronous ingestion and may take 30+ seconds.
    For production use, rely on background schedulers instead of manual API calls.

    Returns immediately after starting background processing.
    Check server logs for completion status.
    """
    try:
        # Import required modules for background processing
        import asyncio
        from backend.agents.social_listening_agent import get_social_listening_agent

        # Start background ingestion (fire and forget)
        async def background_ingestion():
            try:
                print(f"[SocialListening] Starting background ingestion for user {user.id}")
                agent = get_social_listening_agent()
                stats = await agent.process_all_rules(user.id)
                print(f"[SocialListening] Background ingestion completed: {stats}")
            except Exception as e:
                print(f"[SocialListening] Background ingestion failed: {e}")

        # Fire and forget - don't wait for completion
        asyncio.create_task(background_ingestion())

        return {
            "status": "accepted",
            "message": "Background content fetching started. Check server logs for completion.",
            "note": "⚠️  This endpoint is deprecated. Use background schedulers for production ingestion."
        }

    except Exception as e:
        print(f"[SocialListening] Error starting background fetch: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feed Endpoints ====================

@router.get("/feed")
async def get_feed(
    time_range: Optional[str] = Query(None, description="Time range filter: all, today, 24h, 7d, 30d, custom"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)"),
    rule_id: Optional[str] = Query(None, description="Filter by specific rule ID (all for no filter)"),
    platform: Optional[str] = Query(None, description="Filter by platform (all for no filter)"),
    sort_order: Optional[str] = Query(None, description="Sort order: newest or oldest"),
    limit: Optional[int] = Query(None, description="Items per page (1-100)"),
    offset: Optional[int] = Query(None, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get optimized live feed for the current user with pagination.

    PERFORMANCE TARGET: <500ms response time
    READ-ONLY: Never triggers ingestion or external API calls
    """
    start_time = time.time()

    # Apply safe defaults for all parameters
    time_range = time_range or "all"
    platform = platform or "all"
    rule_id = rule_id or "all"
    sort_order = sort_order or "newest"
    limit = min(max(limit or 20, 1), 100)  # Ensure limit is between 1-100
    offset = max(offset or 0, 0)  # Ensure offset is non-negative

    # Log incoming parameters for debugging
    print(f"[FeedAPI] Request params: time_range={time_range}, platform={platform}, rule_id={rule_id}, "
          f"sort_order={sort_order}, limit={limit}, offset={offset}")

    try:
        # Build optimized query with field projection (not full objects)
        # Use indexed columns for filtering and sorting
        stmt = select(
            # MatchedResult fields
            MatchedResult.id,
            MatchedResult.post_id,
            MatchedResult.rule_id,
            MatchedResult.sentiment,
            MatchedResult.sentiment_score,
            MatchedResult.relevance_score,
            MatchedResult.matched_keywords,
            MatchedResult.important,
            MatchedResult.saved,
            MatchedResult.created_at,
            MatchedResult.explanation,
            MatchedResult.timestamp_source,
            MatchedResult.confidence_level,
            # FetchedPost fields
            FetchedPost.platform,
            FetchedPost.author,
            FetchedPost.handle,
            FetchedPost.content,
            FetchedPost.url,
            FetchedPost.posted_at,
            FetchedPost.quality_score,
            # TrackingRule fields
            TrackingRule.name.label("rule_name")
        ).select_from(
            MatchedResult
        ).outerjoin(
            FetchedPost, MatchedResult.post_id == FetchedPost.id
        ).outerjoin(
            TrackingRule, MatchedResult.rule_id == TrackingRule.id
        ).where(
            MatchedResult.user_id == user.id
        )

        # Apply time range filtering (uses indexed posted_at column)
        now = datetime.utcnow()
        if time_range and time_range != "all":
            if time_range == "today":
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                stmt = stmt.where(FetchedPost.posted_at >= today_start)
                print(f"[FeedAPI] Applied time filter: today (since {today_start})")
            elif time_range == "24h":
                last_24h = now - timedelta(hours=24)
                stmt = stmt.where(FetchedPost.posted_at >= last_24h)
                print(f"[FeedAPI] Applied time filter: 24h (since {last_24h})")
            elif time_range == "7d":
                last_7d = now - timedelta(days=7)
                stmt = stmt.where(FetchedPost.posted_at >= last_7d)
                print(f"[FeedAPI] Applied time filter: 7d (since {last_7d})")
            elif time_range == "30d":
                last_30d = now - timedelta(days=30)
                stmt = stmt.where(FetchedPost.posted_at >= last_30d)
                print(f"[FeedAPI] Applied time filter: 30d (since {last_30d})")
            elif time_range == "custom" and start_date and end_date:
                try:
                    start_dt = datetime.fromisoformat(start_date)
                    end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
                    stmt = stmt.where(FetchedPost.posted_at.between(start_dt, end_dt))
                    print(f"[FeedAPI] Applied custom time filter: {start_dt} to {end_dt}")
                except ValueError as e:
                    print(f"[FeedAPI] Invalid custom date format: {e}, ignoring filter")
                    pass  # Invalid date format, ignore
            else:
                print(f"[FeedAPI] Unknown time_range value: {time_range}, ignoring filter")
        else:
            print("[FeedAPI] No time range filter applied (all time)")

        # Apply rule filtering (uses indexed rule_id column)
        if rule_id and rule_id != "all":
            try:
                stmt = stmt.where(MatchedResult.rule_id == int(rule_id))
            except ValueError:
                pass

        # Apply platform filtering (uses indexed platform column)
        if platform and platform != "all":
            stmt = stmt.where(FetchedPost.platform == platform)

        # Apply sorting (uses indexed posted_at DESC)
        if sort_order == "oldest":
            stmt = stmt.order_by(FetchedPost.posted_at.asc())
            print("[FeedAPI] Applied sorting: oldest first")
        else:
            # Default to newest for any other value
            stmt = stmt.order_by(FetchedPost.posted_at.desc())
            print("[FeedAPI] Applied sorting: newest first (default)")

        # Apply pagination (LIMIT + OFFSET)
        stmt = stmt.limit(limit).offset(offset)

        # Execute query with timing
        query_start = time.time()
        result = await db.execute(stmt)
        rows = result.all()
        query_time = time.time() - query_start

        # Build lightweight response (no complex object construction)
        items = []
        for row in rows:
            # Convert row to dict for lightweight JSON response
            item = {
                "id": str(row.id),
                "platform": row.platform or "unknown",
                "author": row.author or "Unknown",
                "handle": row.handle or "",
                "content": row.content or "",
                "url": row.url or "",
                "posted_at": row.posted_at.isoformat() if row.posted_at else None,
                "rule_name": row.rule_name or "Unknown Rule",
                "rule_id": str(row.rule_id) if row.rule_id else "",
                "important": row.important or False,
                "saved": row.saved or False,
                "quality_score": row.quality_score or 5,
                "sentiment": row.sentiment or "neutral",
                "sentiment_score": row.sentiment_score or 0.5,
                "relevance_score": row.relevance_score or 0.5,
                "matched_keywords": row.matched_keywords or [],
                "explanation": row.explanation or "",
                "timestamp_source": row.timestamp_source or "unknown",
                "confidence_level": row.confidence_level or "unknown"
            }
            items.append(item)

        # Calculate total response time
        total_time = time.time() - start_time

        # Performance logging
        if total_time > 0.5:
            print(f"[PERFORMANCE] Slow feed query: {total_time:.2f}s (query: {query_time:.2f}s) - user: {user.id}")

        return {
            "items": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(items) == limit  # Simple has_more indicator
            },
            "filters_applied": {
                "time_range": time_range,
                "start_date": start_date,
                "end_date": end_date,
                "rule_id": rule_id,
                "platform": platform,
                "sort_order": sort_order
            },
            "performance": {
                "total_time_ms": round(total_time * 1000, 2),
                "query_time_ms": round(query_time * 1000, 2),
                "item_count": len(items)
            }
        }

    except Exception as e:
        error_time = time.time() - start_time
        print(f"[SocialListening] Feed error after {error_time:.2f}s: {e}")
        import traceback
        traceback.print_exc()

        # Return structured error response
        return {
            "error": "Feed query failed",
            "message": str(e),
            "items": [],
            "pagination": {"limit": 20, "offset": 0, "has_more": False},
            "filters_applied": {},
            "performance": {"total_time_ms": round(error_time * 1000, 2), "error": str(e)}
        }


@router.post("/feed/{item_id}/mark-important")
async def mark_important(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Mark a feed item as important"""
    try:
        stmt = select(MatchedResult).where(
            MatchedResult.id == item_id,
            MatchedResult.user_id == user.id
        )
        result = await db.execute(stmt)
        match = result.scalar_one_or_none()
        
        if not match:
            raise HTTPException(status_code=404, detail="Item not found")
        
        match.important = True
        await db.commit()
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feed/{item_id}/unmark-important")
async def unmark_important(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Unmark a feed item as important"""
    try:
        stmt = select(MatchedResult).where(
            MatchedResult.id == item_id,
            MatchedResult.user_id == user.id
        )
        result = await db.execute(stmt)
        match = result.scalar_one_or_none()
        
        if not match:
            raise HTTPException(status_code=404, detail="Item not found")
        
        match.important = False
        await db.commit()
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feed/{item_id}/save")
async def save_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Save a feed item"""
    try:
        stmt = select(MatchedResult).where(
            MatchedResult.id == item_id,
            MatchedResult.user_id == user.id
        )
        result = await db.execute(stmt)
        match = result.scalar_one_or_none()
        
        if not match:
            raise HTTPException(status_code=404, detail="Item not found")
        
        match.saved = True
        await db.commit()
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Alerts Endpoints ====================

@router.get("/alerts")
async def get_alerts(
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get alerts for the current user"""
    try:
        stmt = select(SocialAlert).where(
            SocialAlert.user_id == user.id
        ).order_by(desc(SocialAlert.created_at)).limit(limit)
        
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        return {
            "alerts": [
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "message": alert.message,
                    "read": alert.read,
                    "alert_type": alert.alert_type,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        # Return empty list instead of crashing - tables may not exist yet
        print(f"[SocialListening] Error fetching alerts (table may not exist): {e}")
        return {"alerts": []}


@router.post("/alerts/mark-read")
async def mark_all_alerts_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Mark all alerts as read"""
    try:
        stmt = select(SocialAlert).where(
            SocialAlert.user_id == user.id,
            SocialAlert.read == False
        )
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        for alert in alerts:
            alert.read = True
        
        await db.commit()
        
        return {"status": "success", "marked": len(alerts)}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Analytics Endpoints ====================

@router.get("/analytics")
async def get_analytics(
    timeframe: str = "7d",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get analytics data for the current user"""
    # Default empty response
    empty_response = {
        "analytics": {
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "platforms": {"twitter": 0, "linkedin": 0, "reddit": 0, "news": 0},
            "keywords": [],
            "total_posts": 0,
            "timeframe": timeframe
        }
    }
    
    try:
        # Calculate date range
        days = {"7d": 7, "30d": 30, "90d": 90}.get(timeframe, 7)
        start_date = datetime.now() - timedelta(days=days)
        
        # Simple query without sentiment join (tables may not exist yet)
        stmt = select(MatchedResult, FetchedPost).join(
            FetchedPost, MatchedResult.post_id == FetchedPost.id
        ).where(
            MatchedResult.user_id == user.id,
            MatchedResult.created_at >= start_date
        )
        
        result = await db.execute(stmt)
        items = result.all()
        
        if not items:
            return empty_response
        
        # Calculate analytics
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        platform_counts = {"twitter": 0, "linkedin": 0, "reddit": 0, "news": 0}
        keyword_freq = {}
        
        for match, post in items:
            # Platform counts
            if post.platform in platform_counts:
                platform_counts[post.platform] += 1
            
            # Use actual sentiment if available
            sentiment = (match.sentiment or "neutral").lower()
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            else:
                sentiment_counts["neutral"] += 1
            
            # Keyword frequency (extract from content)
            if post.content:
                words = post.content.lower().split()
                for word in words:
                    clean_word = ''.join(c for c in word if c.isalnum())
                    if len(clean_word) > 4:  # Only meaningful words
                        keyword_freq[clean_word] = keyword_freq.get(clean_word, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "analytics": {
                "sentiment": sentiment_counts,
                "platforms": platform_counts,
                "keywords": [{"keyword": k, "count": v} for k, v in top_keywords],
                "total_posts": len(items),
                "timeframe": timeframe
            }
        }
    except Exception as e:
        print(f"[SocialListening] Error fetching analytics: {e}")
        return empty_response


# ==================== AI Response Generation ====================

@router.post("/generate-response")
async def generate_response(
    request: ResponseGenerateRequest,
    user: User = Depends(get_current_user)
):
    """Generate an AI response for a social media post"""
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Build prompt based on intent and tone
        intent_prompts = {
            "supportive": "Write a supportive and encouraging comment",
            "professional": "Write a professional and insightful response",
            "counter": "Write a respectful counter-argument or alternative perspective",
            "neutral": "Write a neutral, factual summary or clarification",
            "promotional": "Write a subtle promotional reply that adds value"
        }
        
        length_guides = {
            "short": "Keep it to 1-2 sentences maximum.",
            "medium": "Write a paragraph (3-5 sentences).",
            "long": "Write a detailed response (2-3 paragraphs)."
        }
        
        prompt = f"""You are a social media engagement expert. {intent_prompts.get(request.intent, intent_prompts['professional'])}.

Original post from {request.platform}:
"{request.original_content}"

Requirements:
- Tone: {request.tone}
- {length_guides.get(request.length, length_guides['medium'])}
- Be authentic and avoid sounding like AI
- Match the platform's communication style ({request.platform})
- Add value to the conversation

Write the response only, no explanations or prefixes."""

        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        
        return {"response": generated_text}
        
    except Exception as e:
        print(f"[SocialListening] Error generating response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")


# ==================== Reports Endpoints ====================

@router.post("/reports/generate")
async def generate_report(
    request: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Generate a clean, readable report"""
    try:
        print(f"[Reports] Generating {request.type} report for user {user.id}")
        print(f"[Reports] Date range: {request.start_date} to {request.end_date}")

        # Parse dates with better error handling
        try:
            start_date = datetime.fromisoformat(request.start_date)
            end_date = datetime.fromisoformat(request.end_date)
            print(f"[Reports] Parsed dates: {start_date} to {end_date}")
        except ValueError as date_error:
            print(f"[Reports] Date parsing error: {date_error}")
            raise HTTPException(status_code=400, detail=f"Invalid date format. Expected YYYY-MM-DD, got: {request.start_date}, {request.end_date}")

        # Generate the report content
        print(f"[Reports] Generating content for {request.type} report...")
        report_content = await generate_report_content(
            db, user.id, request.type, start_date, end_date, request.rule_ids,
            request.platform, request.source, request.min_relevance
        )

        print(f"[Reports] Content generated, length: {len(report_content)} characters")

        # Create report record
        report = MonitoringReport(
            user_id=user.id,
            report_type=request.type,
            start_date=start_date,
            end_date=end_date,
            rules_included=request.rule_ids or [],
            content=report_content
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        print(f"[Reports] Report saved with ID: {report.id}")

        return {
            "status": "success",
            "report_id": str(report.id),
            "report_content": report_content,
            "message": "Report generated successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[Reports] Unexpected error generating report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/reports")
async def get_reports(
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get list of generated reports"""
    try:
        stmt = select(MonitoringReport).where(
            MonitoringReport.user_id == user.id
        ).order_by(desc(MonitoringReport.created_at)).limit(limit)
        
        result = await db.execute(stmt)
        reports = result.scalars().all()
        
        return {
            "reports": [
                {
                    "id": str(report.id),
                    "type": report.report_type,
                    "start_date": report.start_date.isoformat() if report.start_date else None,
                    "end_date": report.end_date.isoformat() if report.end_date else None,
                    "pdf_url": report.pdf_path,
                    "created_at": report.created_at.isoformat() if report.created_at else None
                }
                for report in reports
            ]
        }
    except Exception as e:
        print(f"[SocialListening] Error fetching reports: {e}")
        return {"reports": []}


# =============================================================================
# EMAIL NOTIFICATION SETTINGS
# =============================================================================

class NotificationEmailRequest(BaseModel):
    """Request model for updating notification email"""
    email: EmailStr


@router.post("/user/notification-email")
async def update_notification_email(
    request: NotificationEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the user's notification email for instant alerts

    This endpoint allows users to set their email address for receiving
    immediate notifications when social monitoring rules find new matches.
    """
    try:
        # Update user's notification email
        user.notification_email = request.email
        await db.commit()

        print(f"[Email] Updated notification email for user {user.id}: {request.email}")

        return {
            "success": True,
            "message": "Notification email updated successfully",
            "email": request.email
        }

    except Exception as e:
        print(f"[Email] Error updating notification email: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update notification email"
        )


@router.get("/user/notification-email")
async def get_notification_email(user: User = Depends(get_current_user)):
    """
    Get the user's current notification email setting
    """
    return {
        "email": user.notification_email,
        "has_email": bool(user.notification_email)
    }
