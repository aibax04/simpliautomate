from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.graph import create_graph
from backend.agents.post_generation_agent import PostGenerationAgent
from backend.agents.linkedin_agent import LinkedInAgent
from backend.config import Config
from backend.routes.ingest import router as ingest_router
from backend.routes.queue_router import router as queue_router
from backend.routes.media import setup_media_routes
import google.generativeai as genai
import uvicorn
import asyncio
from backend.agents.news_fetch_agent import NewsFetchAgent

# Configure Gemini globally
genai.configure(api_key=Config.GEMINI_API_KEY)

app = FastAPI(title="Simplii News API")
app.include_router(ingest_router, prefix="/api")
app.include_router(queue_router, prefix="/api")

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
async def fetch_news():
    """Endpoint to fetch and curate live news cards"""
    result = await graph.ainvoke({"news_items": [], "status": "init"})
    return result["news_items"]

@app.post("/api/generate-post")
async def generate_post(request: Request):
    """Endpoint to generate LinkedIn post from selected news"""
    data = await request.json()
    news_item = data.get("news")
    prefs = data.get("prefs")
    
    agent = PostGenerationAgent()
    result = await agent.generate(news_item, prefs)
    return result

@app.post("/api/post-linkedin")
async def post_linkedin(request: Request):
    """Endpoint to trigger LinkedIn posting"""
    data = await request.json()
    content = data.get("content")
    image_url = data.get("image_url")
    
    # Use Config credentials (default behavior of Agent)
    agent = LinkedInAgent() 
    result = agent.post_to_linkedin(content, image_path=image_url)
    return result

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
