import asyncio
import os
import sys

# Ensure backend path
sys.path.append(os.getcwd())

from backend.agents.news_fetch_agent import NewsFetchAgent

async def test_agent():
    print("--- TESTING AGENT ---")
    try:
        agent = NewsFetchAgent()
        print(f"Agent initialized with model: {agent.model_name}")
        
        # Test fetch directly
        print("Calling agent.fetch(force_refresh=True)...")
        news = await agent.fetch(force_refresh=True)
        
        print(f"Fetch completed. Items: {len(news)}")
        for item in news:
            print(f"FOUND: {item.get('headline')}")
            
    except Exception as e:
        print(f"CRITICAL AGENT FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Force output to utf-8
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test_agent())


