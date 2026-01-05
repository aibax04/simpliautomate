from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.queue.queue_manager import QueueManager
from backend.agents.post_generation_agent import PostGenerationAgent
from backend.agents.linkedin_blog_agent import LinkedInBlogAgent
from backend.agents.image_agent import ImageAgent
import asyncio
from backend.db.database import AsyncSessionLocal, get_db
from backend.db.models import GenerationQueue, GeneratedPost, NewsItem, User, Product
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.auth.security import get_current_user

router = APIRouter()
queue = QueueManager()

class EnqueueRequest(BaseModel):
    news_item: Optional[Dict[str, Any]] = None
    user_prefs: Dict[str, Any]
    custom_prompt: Optional[str] = None
    product_id: Optional[int] = None

class BlogEnqueueRequest(BaseModel):
    topic: str
    tone: str = "Professional"
    length: str = "Medium"
    product_id: Optional[int] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

async def _persist_post(news_item: Dict, result: Dict, user_prefs: Dict, user_id: int, job_id_memory: str = None):
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
            await session.flush() # Get db_post.id
            
            # 3. Add to Queue History
            db_job = GenerationQueue(
                user_id=user_id,
                news_id=db_news.id,
                status="ready",
                preferences_json=user_prefs,
                result_json={**result, "post_id": db_post.id}
            )
            session.add(db_job)
            
            await session.commit()
            
            # Also update the in-memory job if possible
            if job_id_memory:
                queue.update_job(job_id_memory, result={**result, "post_id": db_post.id})
            
            print(f"[DB] Persisted post {db_post.id} for user {user_id}: {news_item.get('headline')[:30]}...")
        except Exception as e:
            await session.rollback()
            print(f"[DB ERROR] Post persistence failed: {e}")

async def process_post_generation(job_id: str, news_item: Dict, user_prefs: Dict, user_id: int, product_id: Optional[int] = None):
    """
    Background task wrapper for post generation.
    """
    try:
        # Define progress callback
        async def progress_callback(status, progress):
            queue.update_job(job_id, status=status, progress=progress)
            
        # Fetch product info if requested
        product_info = None
        if product_id:
            async with AsyncSessionLocal() as session:
                stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.collateral))
                res = await session.execute(stmt)
                product = res.scalar_one_or_none()
                if product:
                    product_info = {
                        "name": product.name,
                        "description": product.description,
                        "website_url": product.website_url,
                        "collateral": [
                            {"file_name": c.file_name, "file_path": c.file_path, "file_type": c.file_type}
                            for c in product.collateral
                        ]
                    }

        # Initialize agent
        agent = PostGenerationAgent()
        
        # Run the official workflow with progress updates
        print(f"[Job {job_id}] Starting official workflow for user {user_id}...")
        result = await agent.generate(news_item, user_prefs, on_progress=progress_callback, product_info=product_info)
        
        if result:
            queue.update_job(job_id, status="ready", result=result, progress=100)
            # Background persistence
            asyncio.create_task(_persist_post(news_item, result, user_prefs, user_id, job_id_memory=job_id))
            print(f"[Job {job_id}] Completed.")
        else:
            queue.update_job(job_id, status="failed", error="Content generation returned empty/quality failure")

    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        queue.update_job(job_id, status="failed", error=str(e))

async def process_blog_generation(job_id: str, topic: str, tone: str, length: str, user_id: int, product_id: Optional[int] = None):
    """
    Background task wrapper for LinkedIn blog generation.
    """
    try:
        queue.update_job(job_id, status="fetching_sources", progress=10)
        print(f"[Job {job_id}] Starting blog generation for topic: {topic}...")
        
        # Fetch product info if requested
        product_info = None
        if product_id:
            async with AsyncSessionLocal() as session:
                stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.collateral))
                res = await session.execute(stmt)
                product = res.scalar_one_or_none()
                if product:
                    product_info = {
                        "name": product.name,
                        "description": product.description,
                        "website_url": product.website_url,
                        "collateral": [
                            {"file_name": c.file_name, "file_path": c.file_path, "file_type": c.file_type}
                            for c in product.collateral
                        ]
                    }

        agent = LinkedInBlogAgent()
        
        # We'll simulate progress since the agent doesn't have a callback yet
        # or we could add one if needed, but for now simple steps
        queue.update_job(job_id, status="generating_content", progress=40)
        
        result = await agent.generate_blog(topic, tone, length, product_info=product_info)
        
        if result.get("success"):
            queue.update_job(job_id, status="ready", result=result, progress=100)
            print(f"[Job {job_id}] Blog generation completed.")
        else:
            queue.update_job(job_id, status="failed", error=result.get("error", "Unknown error"))
            
    except Exception as e:
        print(f"[Job {job_id}] Blog Generation Failed: {e}")
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
        user.id,
        request.product_id
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Post generation started in background"
    }

@router.post("/enqueue-blog", response_model=JobResponse)
async def enqueue_blog(
    request: BlogEnqueueRequest, 
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    job_id = queue.create_job("blog_generation", {
        "headline": f"Blog: {request.topic}",
        "topic": request.topic,
        "tone": request.tone,
        "length": request.length
    }, user_id=user.id)
    
    background_tasks.add_task(
        process_blog_generation, 
        job_id, 
        request.topic, 
        request.tone, 
        request.length, 
        user.id,
        request.product_id
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Blog generation started in background"
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

@router.post("/regenerate-image")
async def regenerate_image(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Regenerates ONLY the image for a given job/post.
    """
    job_id = payload.get("job_id")
    post_id = payload.get("post_id")
    
    visual_plan = None
    
    # 1. Try to find in memory queue first
    if job_id:
        job = queue.get_job(job_id)
        if job and "result" in job:
            visual_plan = job["result"].get("visual_plan")
    
    # 2. Try to find in DB history
    if not visual_plan:
        async with AsyncSessionLocal() as session:
            if post_id:
                # Find the queue entry that generated this post
                # We store post_id inside result_json
                from sqlalchemy import text
                stmt = select(GenerationQueue).where(
                    GenerationQueue.user_id == user.id,
                    text("result_json->>'post_id' = :pid").bindparams(pid=str(post_id))
                ).limit(1)
            else:
                # Fallback to most recent job for this user
                stmt = select(GenerationQueue).where(GenerationQueue.user_id == user.id).order_by(GenerationQueue.created_at.desc()).limit(1)
            
            res = await session.execute(stmt)
            db_job = res.scalar_one_or_none()
            if db_job and db_job.result_json:
                visual_plan = db_job.result_json.get("visual_plan")

    if not visual_plan:
        raise HTTPException(status_code=404, detail="Original visual plan not found. Please generate a new post.")

    image_agent = ImageAgent()
    try:
        new_image_url = await image_agent.generate_image(visual_plan)
        return {"image_url": new_image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-post-image")
async def update_post_image(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Updates the image_path for a post after user confirmation.
    """
    image_url = payload.get("image_url")
    post_id = payload.get("post_id")
    
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")

    async with AsyncSessionLocal() as session:
        try:
            if post_id:
                stmt = select(GeneratedPost).where(GeneratedPost.id == post_id, GeneratedPost.user_id == user.id)
            else:
                # Fallback to most recent
                stmt = select(GeneratedPost).where(GeneratedPost.user_id == user.id).order_by(GeneratedPost.created_at.desc()).limit(1)
            
            res = await session.execute(stmt)
            db_post = res.scalar_one_or_none()
            
            if db_post:
                db_post.image_path = image_url
                await session.commit()
                return {"status": "success", "message": "Post image updated"}
            else:
                raise HTTPException(status_code=404, detail="Post not found to update")
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
