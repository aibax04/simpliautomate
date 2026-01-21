import asyncio
import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from backend.utils.timestamp_extractor import get_timestamp_extractor

async def test_extraction():
    extractor = get_timestamp_extractor()
    # Real URL for testing
    url = "https://www.healthcareitnews.com/news/emea/ai-healthcare-uk-government-invests-100m-accelerate-treatment"
    
    print(f"Testing extraction for {url}...")
    result = await extractor.extract(url)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
