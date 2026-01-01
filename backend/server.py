from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.graph import create_graph
from backend.agents.post_generation_agent import PostGenerationAgent
from backend.agents.linkedin_agent import LinkedInAgent
from backend.config import Config
from backend.routes.ingest import router as ingest_router
from backend.routes.queue_router import router as queue_router
from backend.routes.auth import router as auth_router
from backend.routes.media import setup_media_routes
from backend.auth.security import decode_access_token, get_current_user
from fastapi.security import OAuth2PasswordBearer
import google.generativeai as genai
import uvicorn
import asyncio
from backend.agents.news_fetch_agent import NewsFetchAgent
from backend.db.models import GeneratedPost, SavedPost, NewsItem, User
from sqlalchemy import select
from backend.db.database import AsyncSessionLocal, check_db_connection, get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Configure Gemini globally
genai.configure(api_key=Config.GEMINI_API_KEY)

app = FastAPI(title="Simplii News API")

# Routes
app.include_router(auth_router, prefix="/api")
app.include_router(ingest_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(queue_router, prefix="/api", dependencies=[Depends(get_current_user)])

# Background task for constant news fetching
async def background_news_fetcher():
    agent = NewsFetchAgent()
    while True:
        try:
            print("[BACKGROUND] Periodically refreshing news cache...")
            await agent.fetch(force_refresh=True)
        except Exception as e:
            print(f"[BACKGROUND ERROR] {e}")
        await asyncio.sleep(600) # Refresh every 10 minutes

@app.on_event("startup")
async def startup_event():
    # Verify DB connection on startup
    await check_db_connection()
    asyncio.create_task(background_news_fetcher())

# Setup Media Serving (Critical for Image Visibility)
setup_media_routes(app)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangGraph
graph = create_graph()

@app.get("/api/fetch-news")
async def fetch_news(user: User = Depends(get_current_user)):
    """Endpoint to fetch and curate live news cards"""
    result = await graph.ainvoke({"news_items": [], "status": "init"})
    return result["news_items"]

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@app.post("/api/generate-post")
async def generate_post(request: Request, user: User = Depends(get_current_user)):
    """Endpoint to generate LinkedIn post from selected news"""
    data = await request.json()
    news_item = data.get("news")
    prefs = data.get("prefs")
    
    agent = PostGenerationAgent()
    result = await agent.generate(news_item, prefs)
    return result

@app.post("/api/post-linkedin")
async def post_linkedin(request: Request, user: User = Depends(get_current_user)):
    """Endpoint to trigger LinkedIn posting"""
    data = await request.json()
    content = data.get("content")
    image_url = data.get("image_url")
    
    # Use Config credentials (default behavior of Agent)
    agent = LinkedInAgent() 
    result = agent.post_to_linkedin(content, image_path=image_url)
    
    # DB Persistence (Optional update of status)
    if result.get("status") == "success":
        asyncio.create_task(_update_post_status(image_url))
        
    return result

async def _update_post_status(image_url: str):
    """Update DB to mark post as published."""
    if not image_url: return
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(GeneratedPost).where(GeneratedPost.image_path == image_url)
            res = await session.execute(stmt)
            db_post = res.scalar_one_or_none()
            if db_post:
                db_post.posted_to_linkedin = True
                await session.commit()
        except Exception:
            await session.rollback()

@app.post("/api/save-post")
async def save_post(request: Request, user: User = Depends(get_current_user)):
    """Explicitly save a post for the current user."""
    data = await request.json()
    caption = data.get("caption")
    image_url = data.get("image_url")
    notes = data.get("notes", "")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Find the GeneratedPost (or create a shell)
            stmt = select(GeneratedPost).where(GeneratedPost.image_path == image_url)
            res = await session.execute(stmt)
            db_post = res.scalar_one_or_none()
            
            if not db_post:
                # If not found, create a detached post entry for this user
                db_post = GeneratedPost(user_id=user.id, caption=caption, image_path=image_url)
                session.add(db_post)
                await session.flush()
            
            # 2. Save to SavedPosts for this specific user
            db_saved = SavedPost(user_id=user.id, post_id=db_post.id, notes=notes)
            session.add(db_saved)
            await session.commit()
            return {"status": "success", "message": "Post saved to library."}
        except Exception as e:
            await session.rollback()
            return {"status": "error", "message": str(e)}

@app.get("/api/saved-posts")
async def get_saved_posts(user: User = Depends(get_current_user)):
    """Retrieve all saved posts for the current user."""
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(SavedPost, GeneratedPost, NewsItem).join(
                GeneratedPost, SavedPost.post_id == GeneratedPost.id
            ).outerjoin(
                NewsItem, GeneratedPost.news_id == NewsItem.id
            ).where(
                SavedPost.user_id == user.id # Filter by user
            ).order_by(SavedPost.created_at.desc())
            
            res = await session.execute(stmt)
            results = []
            for saved, post, news in res.all():
                results.append({
                    "id": saved.id,
                    "caption": post.caption,
                    "image_url": post.image_path,
                    "notes": saved.notes,
                    "headline": news.headline if news else "Uploaded Content",
                    "created_at": saved.created_at
                })
            return results
        except Exception as e:
            print(f"[DB ERROR] Failed to fetch saved posts: {e}")
            return []

# Serve Frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import socket
    
    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('0.0.0.0', port)) == 0

    port = 8000
    if is_port_in_use(port):
        print(f"[WARNING] Port {port} is busy. Falling back to port {port + 1}...")
        port += 1

    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
