"""
Social Listening API Routes
Handles tracking rules, feed, alerts, analytics, and AI response generation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

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
                                start_date: datetime, end_date: datetime, rule_ids: List[str]):
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
    report_lines.append("- Generated: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    report_lines.append("")

    # Get data based on report type
    try:
        if report_type == "summary":
            print("[Reports] Generating summary report...")
            content = await generate_summary_report(db, user_id, start_date, end_date, rule_ids)
        elif report_type == "detailed":
            print("[Reports] Generating detailed report...")
            content = await generate_detailed_report(db, user_id, start_date, end_date, rule_ids)
        elif report_type == "sentiment":
            print("[Reports] Generating sentiment report...")
            content = await generate_sentiment_report(db, user_id, start_date, end_date, rule_ids)
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
                                end_date: datetime, rule_ids: List[str]):
    """Generate summary report with key metrics"""

    print(f"[Reports] Generating summary report for date range: {start_date} to {end_date}")
    lines = []
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 20)

    try:
        # Get total posts fetched in date range
        stmt = select(func.count(FetchedPost.id)).where(
            and_(
                FetchedPost.created_at >= start_date,
                FetchedPost.created_at <= end_date
            )
        )
        result = await db.execute(stmt)
        total_posts = result.scalar() or 0
        print(f"[Reports] Found {total_posts} total posts")
        lines.append("- Total Posts Monitored: {}".format(total_posts))

        # Get posts by platform
        platform_stmt = select(
            FetchedPost.platform,
            func.count(FetchedPost.id).label('count')
        ).where(
            and_(
                FetchedPost.created_at >= start_date,
                FetchedPost.created_at <= end_date
            )
        ).group_by(FetchedPost.platform)
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
                                 end_date: datetime, rule_ids: List[str]):
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
            FetchedPost.created_at >= start_date,
            FetchedPost.created_at <= end_date,
            TrackingRule.user_id == user_id
        )
    ).order_by(FetchedPost.created_at.desc()).limit(50)

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
                                  end_date: datetime, rule_ids: List[str]):
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
            SentimentAnalysis.created_at >= start_date,
            SentimentAnalysis.created_at <= end_date
        )
    ).group_by(SentimentAnalysis.sentiment)

    sentiment_result = await db.execute(sentiment_stmt)
    sentiment_data = sentiment_result.all()

    if sentiment_data:
        lines.append("- Sentiment Distribution:")
        total = sum(count for _, count in sentiment_data)

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


# ==================== Pydantic Models ====================

class RuleCreate(BaseModel):
    name: str
    keywords: List[str] = []
    handles: List[str] = []
    platforms: List[str] = []
    logic_type: str = "keywords_or_handles"
    frequency: str = "hourly"
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
    Manually trigger fetching content for all active rules.
    This searches DuckDuckGo for keywords/handles and stores matches.
    """
    try:
        agent = get_social_listening_agent()
        stats = await agent.process_all_rules(user.id)
        
        return {
            "status": "success",
            "message": f"Fetched content for {stats['rules_processed']} rules",
            "stats": stats
        }
    except Exception as e:
        print(f"[SocialListening] Error in fetch: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feed Endpoints ====================

@router.get("/feed")
async def get_feed(
    rule_id: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get matched content feed for the current user"""
    try:
        # Build query - using outerjoin to handle missing data gracefully
        stmt = select(MatchedResult, FetchedPost, TrackingRule).outerjoin(
            FetchedPost, MatchedResult.post_id == FetchedPost.id
        ).outerjoin(
            TrackingRule, MatchedResult.rule_id == TrackingRule.id
        ).where(
            MatchedResult.user_id == user.id
        )
        
        if rule_id and rule_id != "all":
            try:
                stmt = stmt.where(MatchedResult.rule_id == int(rule_id))
            except ValueError:
                pass
        
        if platform and platform != "all":
            stmt = stmt.where(FetchedPost.platform == platform)
        
        stmt = stmt.order_by(desc(MatchedResult.created_at)).limit(limit)
        
        result = await db.execute(stmt)
        items = result.all()
        
        return {
            "items": [
                {
                    "id": str(match.id),
                    "platform": post.platform if post else "unknown",
                    "author": post.author if post else "Unknown",
                    "handle": post.handle if post else "",
                    "content": post.content if post else "",
                    "url": post.url if post else "",
                    "posted_at": post.posted_at.isoformat() if post and post.posted_at else None,
                    "rule_name": rule.name if rule else "Unknown Rule",
                    "rule_id": str(rule.id) if rule else "",
                    "important": match.important,
                    "saved": match.saved,
                    "quality_score": post.quality_score if post else 5
                }
                for match, post, rule in items
                if post is not None  # Only include items with valid posts
            ]
        }
    except Exception as e:
        print(f"[SocialListening] Error fetching feed: {e}")
        return {"items": []}


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
            
            # Default to neutral sentiment (sentiment analysis not yet implemented)
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
            db, user.id, request.type, start_date, end_date, request.rule_ids
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
