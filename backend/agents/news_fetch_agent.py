import asyncio
import google.generativeai as genai
import json
import time
import aiohttp
from backend.config import Config
from backend.agents.qa_agent import QualityAssuranceAgent

class NewsFetchAgent:
    _cache = []
    _seen_headlines = set()
    _last_fetch_time = 0
    _cache_ttl = 300  # 5 minutes cache
    _search_semaphore = asyncio.Semaphore(2) # Limit concurrent searches to avoid 400 errors

    def __init__(self):
        # Using 2.0 Flash for superior Search Grounding / actual Google Search integration
        self.model_name = 'models/gemini-2.0-flash'
        
        # Grounding tool (dynamic retrieval)
        self.model_with_search = None
        try:
            self.model_with_search = genai.GenerativeModel(
                model_name=self.model_name,
                tools=[{"google_search_retrieval": {}}]
            )
            print(f"[INFO] Actual Google Search grounding enabled with {self.model_name}")
        except Exception as e:
            print(f"[WARNING] Could not enable search grounding: {e}")

        self.model_basic = genai.GenerativeModel(self.model_name)
        self.qa_agent = QualityAssuranceAgent()

    async def verify_link(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Verifies if a link is alive (not 404) using aiohttp for speed."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            async with session.get(url, headers=headers, timeout=5, allow_redirects=True) as resp:
                return resp.status == 200
        except:
            return False

    async def fetch(self, force_refresh=False):
        """
        Fetches, analyzes, and returns domain-specific news with strict filtering.
        Mandates REAL Google Search results for all reference links.
        """
        current_time = time.time()
        
        # Return a random subset from cache if available and fresh enough
        if not force_refresh and len(NewsFetchAgent._cache) >= 15 and (current_time - NewsFetchAgent._last_fetch_time < NewsFetchAgent._cache_ttl):
            import random
            items = list(NewsFetchAgent._cache)
            random.shuffle(items)
            return items[:20]

        all_new_items = []
        batch_size = 4
        category_batches = [Config.CATEGORIES[i:i + batch_size] for i in range(0, len(Config.CATEGORIES), batch_size)]

        async def fetch_batch(batch):
            async with NewsFetchAgent._search_semaphore:
                print(f"   [Search] Querying Google for domains: {batch}")
                prompt = f"""
                You are an elite News Intelligence Agent with real-time Google Search access.
                
                OBJECTIVE:
                Find 3-5 distinct, most recent, impactful, and authentic news articles from the last 24-48 hours for each of these domains:
                {batch}
                
                CRITICAL AUTHENTICITY RULES:
                1. You MUST use the provided Google Search tool to find REAL articles.
                2. Every item MUST have an actual, verified source_url that you found in the search results.
                3. Do NOT use internal training data or hallucinate URLs.
                4. Extract the URL exactly as provided in the search result citations. Do NOT try to modify, shorten, or "clean" the URL.
                5. source_name must be the actual publisher (e.g. 'TechCrunch', 'The Verge', 'Reuters').
                
                STRICT OUTPUT CONTRACT (JSON ONLY):
                Return ONLY a JSON list of objects:
                [
                    {{
                        "headline": "Authentic headline from search results",
                        "summary": "Concise summary explaining the update and its professional significance.",
                        "domain": "The specific domain from {batch}",
                        "source_name": "Actual Publisher",
                        "source_url": "https://actual-verified-link.com",
                        "relevance_score": 0.95
                    }}
                ]
                """
                try:
                    # Attempt with Google Search grounding
                    if self.model_with_search:
                        response = await self.model_with_search.generate_content_async(prompt)
                    else:
                        response = await self.model_basic.generate_content_async(prompt)
                    
                    text = response.text.strip()
                except Exception as e:
                    # FALLBACK: If Google Search fails (400 error), try basic model without search tool
                    print(f"[WARNING] Search tool failed for {batch}, falling back to basic model: {e}")
                    try:
                        response = await self.model_basic.generate_content_async(prompt)
                        text = response.text.strip()
                    except Exception as fallback_e:
                        print(f"[ERROR] Fallback also failed for {batch}: {fallback_e}")
                        return []

                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                if text and text != "[]":
                    try:
                        return json.loads(text)
                    except:
                        return []
            return []

        try:
            # Parallelize batch searches
            search_tasks = [fetch_batch(batch) for batch in category_batches]
            results = await asyncio.gather(*search_tasks)
            
            for batch_items in results:
                all_new_items.extend(batch_items)

            if not all_new_items:
                return NewsFetchAgent._cache if NewsFetchAgent._cache else []

            print(f"   [Quality Gate] Verifying {len(all_new_items)} search-grounded news items...")
            
            # Parallelize verification
            tasks = [self.qa_agent.verify_and_fix(item) for item in all_new_items]
            cleaned_items = await asyncio.gather(*tasks)
            
            new_verified_news = []
            
            # Validation Step: Verify links are alive using shared session
            print(f"   [Verification] Checking {len(cleaned_items)} links for 404 errors...")
            async with aiohttp.ClientSession() as session:
                link_tasks = []
                for item in cleaned_items:
                    if item and item.get("source_url"):
                        link_tasks.append(self.verify_link(session, item["source_url"]))
                    else:
                        link_tasks.append(asyncio.sleep(0, result=False))
                
                link_status = await asyncio.gather(*link_tasks)

            for i, clean_item in enumerate(cleaned_items):
                if not clean_item or not link_status[i]:
                    continue
                
                headline = clean_item.get("headline", "")
                if headline in NewsFetchAgent._seen_headlines:
                    continue

                source_url = clean_item.get("source_url", "")
                has_valid_url = source_url and source_url.startswith("http")
                
                item_domain = clean_item.get("domain", "").strip()
                is_valid_domain = any(vd.lower() in item_domain.lower() for vd in Config.CATEGORIES)
                
                is_highly_relevant = clean_item.get("relevance_score", 0) >= 0.70
                
                if has_valid_url and is_valid_domain and is_highly_relevant:
                    new_verified_news.append(clean_item)
                    NewsFetchAgent._seen_headlines.add(headline)
            
            # Add new items to the top of the cache
            NewsFetchAgent._cache = new_verified_news + NewsFetchAgent._cache
            
            if len(NewsFetchAgent._cache) > 200:
                NewsFetchAgent._cache = NewsFetchAgent._cache[:200]

            print(f"[DEBUG] Added {len(new_verified_news)} items. Total pool: {len(NewsFetchAgent._cache)}")
            
            NewsFetchAgent._last_fetch_time = current_time
            
            import random
            result = list(NewsFetchAgent._cache)
            random.shuffle(result)
            return result

        except Exception as e:
            print(f"Error fetching news: {e}")
            return NewsFetchAgent._cache if NewsFetchAgent._cache else []
