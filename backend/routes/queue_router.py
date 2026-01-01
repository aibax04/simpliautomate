from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.queue.queue_manager import QueueManager
from backend.agents.post_generation_agent import PostGenerationAgent
import asyncio
from backend.db.database import AsyncSessionLocal, get_db
from backend.db.models import GenerationQueue, GeneratedPost, NewsItem, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.security import get_current_user

router = APIRouter()
queue = QueueManager()

class EnqueueRequest(BaseModel):
    news_item: Optional[Dict[str, Any]] = None
    user_prefs: Dict[str, Any]
    custom_prompt: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

async def _persist_post(news_item: Dict, result: Dict, user_prefs: Dict, user_id: int):
    """Helper to persist generated post to database."""
    async with AsyncSessionLocal() as session:
        try:
            # 1. Find the NewsItem in DB (or create if missing)
            stmt = select(NewsItem).where(NewsItem.headline == news_item.get("headline"))
            res = await session.execute(stmt)
            db_news = res.scalar_one_or_none()
            
            if not db_news:
                db_news = NewsItem(
                    headline=news_item.get("headline"),
                    summary=news_item.get("summary"),
                    category=news_item.get("domain", "General"),
                    source_url=news_item.get("source_url", "")
                )
                session.add(db_news)
                await session.flush()

            # 2. Save Generated Post
            db_post = GeneratedPost(
                user_id=user_id,
                news_id=db_news.id,
                caption=result.get("text"),
                image_path=result.get("image_url"),
                style=user_prefs.get("image_style"),
                palette=user_prefs.get("image_palette")
            )
            session.add(db_post)
            
            # 3. Add to Queue History
            db_job = GenerationQueue(
                user_id=user_id,
                news_id=db_news.id,
                status="ready",
                preferences_json=user_prefs,
                result_json=result
            )
            session.add(db_job)
            
            await session.commit()
            print(f"[DB] Persisted post for user {user_id}: {news_item.get('headline')[:30]}...")
        except Exception as e:
            await session.rollback()
            print(f"[DB ERROR] Post persistence failed: {e}")

async def process_post_generation(job_id: str, news_item: Dict, user_prefs: Dict, user_id: int):
    """
    Background task wrapper for post generation.
    """
    try:
        # Define progress callback
        async def progress_callback(status, progress):
            queue.update_job(job_id, status=status, progress=progress)
            
        # Initialize agent
        agent = PostGenerationAgent()
        
        # Run the official workflow with progress updates
        print(f"[Job {job_id}] Starting official workflow for user {user_id}...")
        result = await agent.generate(news_item, user_prefs, on_progress=progress_callback)
        
        if result:
            queue.update_job(job_id, status="ready", result=result, progress=100)
            # Background persistence
            asyncio.create_task(_persist_post(news_item, result, user_prefs, user_id))
            print(f"[Job {job_id}] Completed.")
        else:
            queue.update_job(job_id, status="failed", error="Content generation returned empty/quality failure")

    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        queue.update_job(job_id, status="failed", error=str(e))

@router.post("/enqueue-post", response_model=JobResponse)
async def enqueue_post(
    request: EnqueueRequest, 
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    # Determine the payload based on whether it's a news item or a custom prompt
    if request.custom_prompt:
        news_payload = {"custom_prompt": request.custom_prompt}
        display_headline = "Custom Post"
    else:
        news_payload = request.news_item
        display_headline = request.news_item.get("headline", "Untitled")

    job_id = queue.create_job("post_generation", {
        "headline": display_headline,
        "source": "Custom" if request.custom_prompt else request.news_item.get("source", "Unknown"),
        "news_item": news_payload,
        "user_prefs": request.user_prefs
    }, user_id=user.id)
    
    background_tasks.add_task(
        process_post_generation, 
        job_id, 
        news_payload, 
        request.user_prefs,
        user.id
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Post generation started in background"
    }

@router.get("/activity-stream")
@router.get("/queue-status")
async def get_activity_stream(user: User = Depends(get_current_user)):
    """Returns the list of background jobs for the current user's activity queue."""
    jobs = queue.get_all_jobs(user_id=user.id)
    job_list = sorted(jobs.values(), key=lambda x: x["created_at"], reverse=True)
    return job_list

@router.get("/job-result/{job_id}")
async def get_job_result(job_id: str):
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
