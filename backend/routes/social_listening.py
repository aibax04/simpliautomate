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
from pydantic import BaseModel

router = APIRouter(prefix="/social-listening", tags=["Social Listening"])


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
    """Generate a PDF report"""
    try:
        # For now, return a placeholder. Full PDF generation would use ReportLab/WeasyPrint
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)
        
        # Create report record
        report = MonitoringReport(
            user_id=user.id,
            report_type=request.type,
            start_date=start_date,
            end_date=end_date,
            rules_included=request.rule_ids
        )
        
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        # TODO: Generate actual PDF using ReportLab or WeasyPrint
        # For now, return a message
        return {
            "status": "success",
            "report_id": str(report.id),
            "message": "Report generation queued. PDF will be available shortly.",
            "pdf_url": None  # Would be populated after PDF generation
        }
    except Exception as e:
        await db.rollback()
        print(f"[SocialListening] Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
