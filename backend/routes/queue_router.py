from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from backend.queue.queue_manager import QueueManager
from backend.agents.post_generation_agent import PostGenerationAgent

router = APIRouter()
queue = QueueManager()

class EnqueueRequest(BaseModel):
    news_item: Dict[str, Any]
    user_prefs: Dict[str, Any]

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

async def process_post_generation(job_id: str, news_item: Dict, user_prefs: Dict):
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
        print(f"[Job {job_id}] Starting official workflow...")
        result = await agent.generate(news_item, user_prefs, on_progress=progress_callback)
        
        if result:
            queue.update_job(job_id, status="ready", result=result, progress=100)
            print(f"[Job {job_id}] Completed.")
        else:
            queue.update_job(job_id, status="failed", error="Content generation returned empty/quality failure")

    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        queue.update_job(job_id, status="failed", error=str(e))

@router.post("/enqueue-post", response_model=JobResponse)
async def enqueue_post(request: EnqueueRequest, background_tasks: BackgroundTasks):
    job_id = queue.create_job("post_generation", {
        "headline": request.news_item.get("headline", "Untitled"),
        "source": request.news_item.get("source", "Unknown"),
        "news_item": request.news_item,
        "user_prefs": request.user_prefs
    })
    
    background_tasks.add_task(
        process_post_generation, 
        job_id, 
        request.news_item, 
        request.user_prefs
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Post generation started in background"
    }

@router.get("/queue-status")
async def get_queue_status():
    jobs = queue.get_all_jobs()
    # Convert dict items to list for frontend
    # Sort by created_at desc
    job_list = sorted(jobs.values(), key=lambda x: x["created_at"], reverse=True)
    return job_list

@router.get("/job-result/{job_id}")
async def get_job_result(job_id: str):
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
