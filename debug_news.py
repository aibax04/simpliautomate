import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.append(os.getcwd())

from backend.config import Config
from backend.agents.news_fetch_agent import NewsFetchAgent
from backend.tools.google_cse_search import search_google_cse, search_ddg

async def test_search():
    print("--- TESTING SEARCH ---")
    print(f"Categories: {Config.CATEGORIES}")
    
    query = f"recent news {Config.CATEGORIES[0]} 2026"
    print(f"Querying: {query}")
    
    print("\n1. Testing Google CSE...")
    try:
        res = search_google_cse(query, max_results=3)
        print(f"Google CSE Results: {len(res)}")
        for r in res:
            print(f" - {r.get('title')}")
    except Exception as e:
        print(f"Google CSE Failed: {e}")

    print("\n2. Testing DDG Fallback...")
    try:
        res = search_ddg(query, max_results=3)
        print(f"DDG Results: {len(res)}")
        for r in res:
            print(f" - {r.get('title')}")
    except Exception as e:
        print(f"DDG Failed: {e}")

async def test_agent():
    print("\n--- TESTING AGENT ---")
    agent = NewsFetchAgent()
    print("Agent initialized.")
    
    print("Running fetch(force_refresh=True)...")
    try:
        news = await agent.fetch(force_refresh=True)
        print(f"Fetched {len(news)} items.")
        for item in news[:3]:
            print(f" - {item.get('headline')} ({item.get('source_name')})")
    except Exception as e:
        print(f"Agent fetch failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
    asyncio.run(test_agent())
