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
            # 1. Find the NewsItem in DB (or create if missing)
            headline = news_item.get("headline")
            # Fallback for custom posts
            if not headline:
                if news_item.get("custom_prompt"):
                    headline = f"Custom: {news_item.get('custom_prompt')[:50]}"
                else:
                    headline = "Untitled Post"

            stmt = select(NewsItem).where(NewsItem.headline == headline)
            res = await session.execute(stmt)
            db_news = res.scalar_one_or_none()
            
            if not db_news:
                db_news = NewsItem(
                    headline=headline,
                    summary=news_item.get("summary") or news_item.get("custom_prompt") or "No summary",
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
            
            print(f"[DB] Persisted post {db_post.id} for user {user_id}: {headline[:30]}...")
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
        "source": "Custom" if request.custom_prompt is not None else request.news_item.get("source", "Unknown"),
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
    """Returns the combined list of active in-memory jobs and historical database jobs."""
    # 1. Get active jobs from memory
    active_jobs = queue.get_all_jobs(user_id=user.id)
    
    # Create a set of headlines from active 'ready' jobs to prevent duplication
    active_ready_headlines = {
        j.get("payload", {}).get("headline") or j.get("headline") 
        for j in active_jobs.values() 
        if j.get("status") == "ready"
    }
    
    # 2. Get historical jobs from database with headlines
    async with AsyncSessionLocal() as session:
        stmt = select(GenerationQueue, NewsItem).outerjoin(
            NewsItem, GenerationQueue.news_id == NewsItem.id
        ).where(
            GenerationQueue.user_id == user.id
        ).order_by(
            GenerationQueue.created_at.desc()
        ).limit(20)
        
        res = await session.execute(stmt)
        results = res.all()
    
    # 3. Convert DB jobs to the same format as memory jobs
    formatted_db_jobs = []
    for db_j, news in results:
        headline = news.headline if news else "Historical Post"
        category = news.category if news else "General"
        
        # DEDUPLICATION: If this job is already showing as 'ready' in memory, skip the DB version
        # This prevents the "News Post" vs "Past Post" double-listing
        if headline in active_ready_headlines:
            continue
        
        formatted_db_jobs.append({
            "id": f"db_{db_j.id}",
            "job_id": f"db_{db_j.id}",
            "status": db_j.status,
            "created_at": db_j.created_at.isoformat() if db_j.created_at else None,
            "payload": {
                "headline": headline,
                "category": category, # Injected for frontend usage
            },
            "result": db_j.result_json,
            "progress": 100 if db_j.status == "ready" else 0,
            "is_historical": True
        })

    # 4. Merge and sort
    all_jobs = list(active_jobs.values()) + formatted_db_jobs
    
    # De-duplicate by some heuristic if needed, but usually memory ones are 'active' 
    # and DB ones are 'ready/completed'.
    
    # Sort by created_at desc
    job_list = sorted(all_jobs, key=lambda x: x.get("created_at") or "", reverse=True)
    return job_list

@router.get("/job-result/{job_id}")
async def get_job_result(job_id: str):
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

async def _get_visual_plan(user_id: int, job_id: Optional[str] = None, post_id: Optional[int] = None) -> Optional[dict]:
    """Helper to retrieve visual plan from memory or database."""
    visual_plan = None
    print(f"[DEBUG] _get_visual_plan - Job ID: {job_id}, Post ID: {post_id}")
    
    # 1. Try to find in memory queue first
    if job_id:
        job = queue.get_job(job_id)
        if job and "result" in job:
            visual_plan = job["result"].get("visual_plan")
            if visual_plan:
                print(f"[DEBUG] Found visual plan in memory queue.")
    
    # 2. Try to find in DB history
    if not visual_plan:
        async with AsyncSessionLocal() as session:
            try:
                if post_id:
                    print(f"[DEBUG] Searching DB for post_id: {post_id}")
                    # Using text contains for extreme robustness
                    from sqlalchemy import text
                    stmt = select(GenerationQueue).where(
                        GenerationQueue.user_id == user_id,
                        text("CAST(result_json->>'post_id' AS TEXT) = :pid").bindparams(pid=str(post_id))
                    ).limit(1)
                    
                    res = await session.execute(stmt)
                    db_job = res.scalar_one_or_none()
                    if db_job and db_job.result_json:
                        visual_plan = db_job.result_json.get("visual_plan")
                        if visual_plan:
                            print(f"[DEBUG] Found visual plan in DB by post_id: {post_id}")
                
                if not visual_plan:
                    print(f"[DEBUG] Falling back to most recent job for user {user_id}")
                    stmt = select(GenerationQueue).where(
                        GenerationQueue.user_id == user_id,
                        GenerationQueue.status == 'ready'
                    ).order_by(GenerationQueue.created_at.desc()).limit(1)
                    res = await session.execute(stmt)
                    db_job = res.scalar_one_or_none()
                    if db_job and db_job.result_json:
                        visual_plan = db_job.result_json.get("visual_plan")
                        if visual_plan:
                            print(f"[DEBUG] Found visual plan in DB by fallback (most recent ready job).")
            except Exception as e:
                print(f"[ERROR] DB lookup for visual plan failed: {e}")
    
    if not visual_plan:
        print(f"[WARNING] No visual plan found for user {user_id} (Job: {job_id}, Post: {post_id})")
    
    return visual_plan

@router.post("/regenerate-image")
async def regenerate_image(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Regenerates ONLY the image for a given job/post.
    """
    job_id = payload.get("job_id")
    post_id = payload.get("post_id")
    
    if post_id:
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            pass
            
    visual_plan = await _get_visual_plan(user.id, job_id, post_id)

    if not visual_plan:
        raise HTTPException(status_code=404, detail="Original visual plan not found. Please generate a new post.")

    image_agent = ImageAgent()
    try:
        new_image_url = await image_agent.generate_image(visual_plan)
        return {"image_url": new_image_url}
    except Exception as e:
        print(f"[ERROR] Image regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/edit-image")
async def edit_image(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Manually edits the image based on user prompt.
    """
    job_id = payload.get("job_id")
    post_id = payload.get("post_id")
    edit_prompt = payload.get("edit_prompt")

    print(f"[DEBUG] edit_image endpoint called - Job: {job_id}, Post: {post_id}")

    if post_id:
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            pass

    if not edit_prompt:
        print("[ERROR] edit_prompt is missing in payload")
        raise HTTPException(status_code=400, detail="edit_prompt is required")

    visual_plan = await _get_visual_plan(user.id, job_id, post_id)

    if not visual_plan:
        print(f"[ERROR] No visual plan found for Job: {job_id}, Post: {post_id}")
        raise HTTPException(status_code=404, detail="Original visual plan not found. Please generate a new post.")

    image_agent = ImageAgent()
    try:
        print(f"[DEBUG] Calling image_agent.edit_image with prompt: {edit_prompt[:50]}...")
        new_image_url = await image_agent.edit_image(visual_plan, edit_prompt)
        print(f"[SUCCESS] New image generated: {new_image_url}")
        return {"image_url": new_image_url}
    except Exception as e:
        print(f"[ERROR] Image editing failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate-caption")
async def regenerate_caption(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Regenerates only the caption (text) for an existing post, keeping the same image.
    """
    job_id = payload.get("job_id")
    post_id = payload.get("post_id")

    print(f"[DEBUG] regenerate_caption called - Job: {job_id}, Post: {post_id}")

    if post_id:
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            pass

    # Get the original news item and user preferences
    visual_plan = await _get_visual_plan(user.id, job_id, post_id)

    if not visual_plan:
        raise HTTPException(status_code=404, detail="Original visual plan not found. Please generate a new post.")

    # Extract original data from visual plan
    news_item = visual_plan.get('original_news_item', {})
    user_prefs = visual_plan.get('user_prefs', {})

    if not news_item:
        # Try to reconstruct from visual plan
        news_item = {
            'headline': visual_plan.get('headline_hierarchy', {}).get('main', 'Generated Content'),
            'summary': visual_plan.get('headline_hierarchy', {}).get('main', ''),
            'domain': visual_plan.get('domain', 'General'),
            'source_name': 'Caption Regeneration',
            'source_url': '',
            'is_custom': visual_plan.get('is_custom', False)
        }

    try:
        from backend.agents.caption_agent import CaptionStrategyAgent
        from backend.agents.qa_agent import QualityAssuranceAgent

        # Generate new caption
        caption_agent = CaptionStrategyAgent()
        new_caption_data = await caption_agent.generate_caption(news_item, user_prefs)

        # Quality check the new caption
        qa_agent = QualityAssuranceAgent()
        verified_caption = await qa_agent.verify_and_fix(new_caption_data)

        if not verified_caption:
            raise Exception("Generated caption failed quality check")

        # Format the response
        new_caption = verified_caption.get('full_caption', '')
        new_preview = verified_caption.get('hook', '')
        new_hashtags = verified_caption.get('hashtags', '')

        print(f"[SUCCESS] Caption regenerated successfully")
        return {
            "caption": new_caption,
            "preview_text": new_preview,
            "hashtags": new_hashtags,
            "caption_data": verified_caption
        }

    except Exception as e:
        print(f"[ERROR] Caption regeneration failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Caption regeneration failed: {str(e)}")

@router.post("/update-post-image")
async def update_post_image(payload: Dict[str, Any], user: User = Depends(get_current_user)):
    """
    Updates the image_path and optional edit prompt for a post after user confirmation.
    """
    image_url = payload.get("image_url")
    post_id = payload.get("post_id")
    edit_prompt = payload.get("edit_prompt")
    
    if post_id:
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            pass

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
                if edit_prompt:
                    db_post.last_image_edit_prompt = edit_prompt
                
                # Also sync with GenerationQueue history
                try:
                    from sqlalchemy import text
                    q_stmt = select(GenerationQueue).where(
                        GenerationQueue.user_id == user.id,
                        text("CAST(result_json->>'post_id' AS TEXT) = :pid").bindparams(pid=str(db_post.id))
                    ).limit(1)
                    q_res = await session.execute(q_stmt)
                    db_job = q_res.scalar_one_or_none()
                    
                    if db_job:
                        # Update result_json with new image_url and possibly updated visual_plan if needed
                        # but image_url is the primary sync target
                        new_result = dict(db_job.result_json)
                        new_result["image_url"] = image_url
                        db_job.result_json = new_result
                        print(f"[DEBUG] Synced image update to GenerationQueue {db_job.id}")
                except Exception as sync_e:
                    print(f"[WARNING] Syncing to queue history failed: {sync_e}")

                await session.commit()
                print(f"[SUCCESS] Updated post {db_post.id} with new image.")
                return {"status": "success", "message": "Post image updated successfully"}
            else:
                print(f"[ERROR] Post {post_id} not found for user {user.id}")
                raise HTTPException(status_code=404, detail="Post not found to update")
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] update-post-image failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/queue/{job_id}")
async def delete_job(job_id: str, user: User = Depends(get_current_user)):
    """
    Deletes a job from the queue (memory or DB).
    """
    post_id_to_delete = None
    
    # 1. Check memory first
    memory_job = queue.get_job(job_id)
    if memory_job:
        # If it has a result with post_id, we should also try to delete the DB history for it
        if memory_job.get("result") and isinstance(memory_job["result"], dict):
            post_id_to_delete = memory_job["result"].get("post_id")
        
        # Delete from memory
        queue.delete_job(job_id)
        print(f"[Queue] Deleted memory job {job_id}")

    # 2. Determine DB ID to delete
    db_job_id = None
    if job_id.startswith("db_"):
        try:
            db_job_id = int(job_id.split("_")[1])
        except:
            pass
            
    # 3. Perform DB deletion logic
    if db_job_id or post_id_to_delete:
        async with AsyncSessionLocal() as session:
            try:
                stmt = None
                if db_job_id:
                    # Direct deletion by GenerationQueue ID
                    stmt = select(GenerationQueue).where(GenerationQueue.id == db_job_id, GenerationQueue.user_id == user.id)
                elif post_id_to_delete:
                    # Deletion by linked Post ID (found in result_json)
                    from sqlalchemy import text
                    stmt = select(GenerationQueue).where(
                        GenerationQueue.user_id == user.id,
                        text("CAST(result_json->>'post_id' AS TEXT) = :pid").bindparams(pid=str(post_id_to_delete))
                    )
                
                if stmt is not None:
                    res = await session.execute(stmt)
                    # Use unique() if needed, or scalars
                    # db_job = res.scalar_one_or_none() 
                    # multiple matches theoretically possible for post_id if bugs, but scalar is fine
                    db_jobs = res.scalars().all()
                    
                    for db_job in db_jobs:
                        await session.delete(db_job)
                        print(f"[DB] Deleted GenerationQueue record {db_job.id}")
                    
                    await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"[ERROR] Failed to delete job from DB: {e}")
    
    return {"status": "success", "message": "Job deleted"}
