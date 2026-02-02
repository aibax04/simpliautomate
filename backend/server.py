from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone
from backend.graph import create_graph
from backend.agents.post_generation_agent import PostGenerationAgent
from backend.agents.linkedin_agent import LinkedInAgent
from backend.agents.linkedin_blog_agent import LinkedInBlogAgent
from backend.config import Config
from backend.routes.ingest import router as ingest_router
from backend.routes.queue_router import router as queue_router
from backend.routes.auth import router as auth_router
from backend.routes.linkedin import router as linkedin_router
from backend.routes.products import router as products_router
from backend.routes.scheduler import router as scheduler_router
from backend.routes.media import setup_media_routes
from backend.routes.social_listening import router as social_listening_router
from backend.routes.social_ingestion import router as social_ingestion_router
from backend.integrations.whatsapp import router as whatsapp_router
from backend.auth.security import decode_access_token, get_current_user, decrypt_token
from backend.db.models import User
from fastapi.security import OAuth2PasswordBearer
import google.generativeai as genai
import uvicorn
import asyncio
from backend.agents.news_fetch_agent import NewsFetchAgent
from backend.db.models import GeneratedPost, SavedPost, NewsItem, User, LinkedInAccount, ScheduledPost
from sqlalchemy import select, update
from backend.db.database import AsyncSessionLocal, check_db_connection, get_db
from sqlalchemy.ext.asyncio import AsyncSession

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini globally
genai.configure(api_key=Config.GEMINI_API_KEY)

app = FastAPI(title="Simplii News API")

# Routes
app.include_router(auth_router, prefix="/api")
app.include_router(linkedin_router, prefix="/api")
app.include_router(products_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(scheduler_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(ingest_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(queue_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(social_listening_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(social_ingestion_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(whatsapp_router) # Webhook (Public)

# Background task for daily morning news fetching and database saving with fallbacks
async def background_news_fetcher():
    from datetime import datetime, date
    agent = NewsFetchAgent()

    # --- Startup Check: Fetch immediately if today's news is missing ---
    try:
        print("[DAILY NEWS] Startup: Checking for today's news...")
        async with AsyncSessionLocal() as session:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(NewsItem).where(NewsItem.created_at >= today_start).limit(5)
            res = await session.execute(stmt)
            existing = res.all()

            if not existing or len(existing) < 5:
                print("[DAILY NEWS] Startup: Insufficient news for today. Triggering immediate fetch...")
                
                # Reset counts for the new day
                current_date = datetime.now().strftime('%Y-%m-%d')
                agent._daily_fetch_count = 0
                agent._last_reset_date = current_date

                # Fetch and Save
                news_items = await agent.fetch(force_refresh=True)
                if news_items:
                    await agent.save_news_to_database_with_retry(news_items)
                    print(f"[DAILY NEWS] Startup: Saved {len(news_items)} items to DB.")
                else:
                    # Try fallback if main fetch fails
                    print("[DAILY NEWS] Startup: Main fetch empty, trying fallback...")
                    news_items = await agent.fetch_fallback()
                    if news_items:
                        await agent.save_news_to_database_with_retry(news_items)
            else:
                print("[DAILY NEWS] Startup: Today's news already available.")

    except Exception as e:
        print(f"[DAILY NEWS] Startup check warning: {e}")
    # -------------------------------------------------------------

    while True:
        try:
            now = datetime.now()
            # Calculate seconds until 6 AM tomorrow
            tomorrow_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:
                tomorrow_6am = tomorrow_6am.replace(day=now.day + 1)

            seconds_until_6am = (tomorrow_6am - now).total_seconds()

            print(f"[DAILY NEWS] Next fetch scheduled for {tomorrow_6am.strftime('%Y-%m-%d %H:%M:%S')} (in {seconds_until_6am:.0f} seconds)")
            await asyncio.sleep(seconds_until_6am)

            print("[DAILY NEWS] Starting morning news fetch...")
            news_date = now.strftime('%Y-%m-%d')

            # Reset daily counter for fresh start
            agent._daily_fetch_count = 0
            agent._last_reset_date = news_date

            # Attempt 1: Normal fetch
            print("[DAILY NEWS] Attempt 1: Standard news fetch")
            news_items = await agent.fetch(force_refresh=True)

            if not news_items or len(news_items) < 5:
                print(f"[DAILY NEWS] Attempt 1 failed or insufficient news ({len(news_items) if news_items else 0} items). Starting fallbacks...")

                # Attempt 2: Fallback fetch with extended search
                print("[DAILY NEWS] Attempt 2: Extended search fallback")
                news_items = await agent.fetch_fallback()

                if not news_items or len(news_items) < 5:
                    print(f"[DAILY NEWS] Attempt 2 failed. Starting emergency fetch...")

                    # Attempt 3: Emergency fetch with simplified logic
                    print("[DAILY NEWS] Attempt 3: Emergency simplified fetch")
                    news_items = await agent.fetch_emergency()

            # Save to database with retries
            if news_items and len(news_items) > 0:
                saved_count = await agent.save_news_to_database_with_retry(news_items)
                if saved_count > 0:
                    print(f"[DAILY NEWS] ✅ Successfully saved {saved_count} news items to database for {news_date}")
                else:
                    print(f"[DAILY NEWS] ❌ Database save failed for {news_date}")
                    # Try alternative save methods
                    await agent.save_news_emergency(news_items, news_date)
            else:
                print(f"[DAILY NEWS] ❌ No news items available for {news_date}")
                # Try minimal emergency news generation
                await agent.generate_minimal_news(news_date)

        except Exception as e:
            print(f"[DAILY NEWS ERROR] Critical failure: {e}")
            import traceback
            traceback.print_exc()
            # Immediate retry in 30 minutes for critical failures
            await asyncio.sleep(1800)

async def post_scheduler():
    """Background task to publish scheduled posts."""
    from backend.utils.email_sender import send_email
    while True:
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                stmt = select(ScheduledPost, User, LinkedInAccount).join(
                    User, ScheduledPost.user_id == User.id
                ).join(
                    LinkedInAccount, ScheduledPost.linkedin_account_id == LinkedInAccount.id
                ).where(
                    ScheduledPost.status == "pending",
                    ScheduledPost.scheduled_at <= now
                )
                
                res = await session.execute(stmt)
                due_posts = res.all()
                
                for post, user, account in due_posts:
                    print(f"[SCHEDULER] Publishing post {post.id} for user {user.username}...")
                    print(f"[SCHEDULER DEBUG] Image URL from DB: {post.image_url}")
                    
                    access_token = decrypt_token(account.access_token)
                    person_urn = account.linkedin_person_urn
                    
                    agent = LinkedInAgent(access_token=access_token, person_urn=person_urn)
                    result = agent.post_to_linkedin(post.content, image_path=post.image_url)
                    
                    if result.get("status") == "success":
                        post.status = "completed"
                        print(f"[SCHEDULER] Post {post.id} published successfully.")
                        
                        # Send confirmation email
                        target_email = post.notification_email or user.email
                        subject = "LinkedIn Post Published Successfully"
                        body = f"<h1>Great news {user.username}!</h1><p>Your scheduled post was published successfully to LinkedIn.</p><p><strong>Account:</strong> {account.display_name}</p><p><strong>Content:</strong> {post.content[:100]}...</p>"
                        send_email(target_email, subject, body)
                    else:
                        post.status = "failed"
                        post.error_message = result.get("error")
                        print(f"[SCHEDULER] Post {post.id} failed: {post.error_message}")
                        
                        # Send failure email
                        target_email = post.notification_email or user.email
                        subject = "LinkedIn Post Publication Failed"
                        body = f"<h1>Attention {user.username},</h1><p>Your scheduled post failed to publish.</p><p><strong>Error:</strong> {post.error_message}</p><p>Please check your LinkedIn connection and try again.</p>"
                        send_email(target_email, subject, body)
                
                await session.commit()
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        
        await asyncio.sleep(60) # Check every minute

@app.on_event("startup")
async def startup_event():
    # 1. Skip schema verification in production to avoid conflicts
    print("[DB] Skipping schema verification - using existing database structure")

    # 2. Verify DB connection on startup
    await check_db_connection()
    asyncio.create_task(background_news_fetcher())  # ENABLED: Daily morning news generation
    asyncio.create_task(post_scheduler())
    asyncio.create_task(social_listening_scheduler())

async def social_listening_scheduler():
    """Background task to fetch social listening content based on rule frequency."""
    from backend.agents.social_listening_agent import get_social_listening_agent
    
    print("[SCHEDULER] Starting social listening scheduler...")
    while True:
        try:
            agent = get_social_listening_agent()
            await agent.process_due_rules()
        except Exception as e:
            print(f"[SCHEDULER ERROR] Social listening failure: {e}")
        
        # Check every minute (sufficient for 15m granularity)
        await asyncio.sleep(60)

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/fetch-news")
async def fetch_news(q: str = None, force: bool = False, user: User = Depends(get_current_user)):
    """Endpoint to fetch and curate live news cards, supports optional search query 'q' and 'force' refresh"""

    # If no search query and not forced, check database for today's news first
    if not q and not force:
        try:
            from backend.db.database import AsyncSessionLocal
            from backend.db.models import NewsItem
            from datetime import datetime, date
            from sqlalchemy import select, desc

            async with AsyncSessionLocal() as session:
                # Get today's news from database with source information
                from backend.db.models import Source
                today = date.today()
                stmt = select(NewsItem, Source).join(
                    Source, NewsItem.source_id == Source.id
                ).where(
                    NewsItem.created_at >= today
                ).order_by(desc(NewsItem.created_at)).limit(20)

                result = await session.execute(stmt)
                db_results = result.all()

                if db_results and len(db_results) >= 5:
                    # Convert database news to frontend format
                    news_items = []
                    for news_item, source in db_results:
                        news_items.append({
                            "headline": news_item.headline,
                            "summary": news_item.summary,
                            "domain": news_item.category,
                            "source_name": source.name if source else "Daily News",
                            "source_url": news_item.source_url,
                            "relevance_score": 0.9,
                            "id": f"db_{news_item.id}",
                            "timestamp": news_item.created_at.isoformat() if news_item.created_at else None
                        })

                    print(f"[NEWS] Served {len(news_items)} news items from database")
                    return news_items
                else:
                    print("[NEWS] No recent database news found, falling back to live fetch")

        except Exception as e:
            print(f"[NEWS] Database check failed: {e}, falling back to live fetch")

    # Fallback to live fetching (original behavior)
    state = {"news_items": [], "status": "init", "force_refresh": force}
    if q:
        state["search_query"] = q

    result = await graph.ainvoke(state)
    news_items = result.get("news_items", [])

    # NEW: Persist fetched news to database for future requests today
    if not q and news_items: # Only save general news, not search results
        try:
            print(f"[NEWS] Persisting {len(news_items)} live-fetched items to database...")
            # Create fresh agent instance for saving
            save_agent = NewsFetchAgent()
            # Use create_task to run in background so we return response faster, 
            # OR await if we want to be sure. Await is safer for now.
            await save_agent.save_news_to_database_with_retry(news_items)
        except Exception as e:
            print(f"[NEWS] Failed to persist news: {e}")

    return news_items

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
    product_info = data.get("product")
    
    agent = PostGenerationAgent()
    result = await agent.generate(news_item, prefs, product_info=product_info)
    
    # DB Persistence: Save the generated post automatically
    async with AsyncSessionLocal() as session:
        try:
            # Check if news_id is a valid integer (it might be prefixed with db_ if from frontend)
            news_id = result.get("news_id")
            
            db_post = GeneratedPost(
                user_id=user.id,
                news_id=news_id,
                caption=result.get("text"),
                image_path=result.get("image_url"),
                style=result.get("visual_plan", {}).get("style"),
                palette=result.get("visual_plan", {}).get("palette_preference")
            )
            session.add(db_post)
            await session.commit()
            print(f"[DB] Generated post saved automatically with ID: {db_post.id}")
        except Exception as e:
            await session.rollback()
            print(f"[DB ERROR] Failed to save generated post: {e}")

    return result

@app.post("/api/generate-blog")
async def generate_blog(request: Request, user: User = Depends(get_current_user)):
    """Endpoint to generate long-form LinkedIn blog using DuckDuckGo and Gemini 2.5"""
    data = await request.json()
    topic = data.get("topic")
    tone = data.get("tone", "Professional")
    length = data.get("length", "Medium")
    
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    
    agent = LinkedInBlogAgent()
    result = await agent.generate_blog(topic, tone, length)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    return result

@app.post("/api/post-linkedin")
async def post_linkedin(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Endpoint to trigger LinkedIn posting"""
    data = await request.json()
    content = data.get("content")
    image_url = data.get("image_url")
    account_id = data.get("linkedin_account_id")
    
    access_token = None
    person_urn = None

    if account_id:
        # Ensure account_id is an integer to avoid DB type mismatch
        try:
            account_id_int = int(account_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid LinkedIn account ID format")

        # Use specific account
        stmt = select(LinkedInAccount).where(
            LinkedInAccount.id == account_id_int,
            LinkedInAccount.simplii_user_id == user.id
        )
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="LinkedIn account not found")
        
        # Check if token is expired
        if account.token_expires_at and account.token_expires_at < datetime.now(timezone.utc):
             raise HTTPException(status_code=401, detail="LinkedIn account connection expired. Please reconnect.")

        access_token = decrypt_token(account.access_token)
        person_urn = account.linkedin_person_urn
    
    # Use Config credentials if no account specified (legacy/default behavior)
    agent = LinkedInAgent(access_token=access_token, person_urn=person_urn) 
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

    port = 35000
    if is_port_in_use(port):
        print(f"[WARNING] Port {port} is busy. Falling back to port {port + 1}...")
        port += 1

    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
