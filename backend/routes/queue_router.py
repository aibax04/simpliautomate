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
        queue.update_job(job_id, status="generating_caption", progress=25)
        
        # Initialize agent
        agent = PostGenerationAgent()
        
        # We need to hook into the agent's progress if possible, 
        # but for now we'll just run it. 
        # Ideally PostGenerationAgent would support a callback, 
        # but we can simulate progress update here if we split the agent calls.
        
        # 1. Caption
        print(f"[Job {job_id}] Generating caption...")
        caption_data = await agent.caption_agent.generate_caption(news_item, user_prefs)
        queue.update_job(job_id, status="generating_visual_plan", progress=50)
        
        # 2. Visual Plan
        print(f"[Job {job_id}] Planning visual...")
        visual_plan = await agent.visual_agent.plan_visual(news_item, caption_data)
        queue.update_job(job_id, status="generating_image", progress=75)
        
        # 3. Image
        print(f"[Job {job_id}] Generating image...")
        image_url = await agent.image_agent.generate_image(visual_plan)
        
        # 4. Assembly
        final_content = f"{caption_data.get('full_caption')}"
        
        result = {
            "text": final_content,
            "preview_text": caption_data.get('hook'),
            "caption_data": caption_data,
            "image_url": image_url,
            "visual_plan": visual_plan
        }
        
        queue.update_job(job_id, status="ready", result=result, progress=100)
        print(f"[Job {job_id}] Completed.")
        
    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        queue.update_job(job_id, status="failed", error=str(e))

@router.post("/enqueue-post", response_model=JobResponse)
async def enqueue_post(request: EnqueueRequest, background_tasks: BackgroundTasks):
    job_id = queue.create_job("post_generation", {
        "headline": request.news_item.get("headline", "Untitled"),
        "source": request.news_item.get("source", "Unknown")
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
