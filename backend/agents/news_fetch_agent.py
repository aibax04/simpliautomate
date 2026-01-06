import asyncio
from typing import List, Dict
import google.generativeai as genai
import json
import time
import aiohttp
import sys
from backend.config import Config
from backend.agents.qa_agent import QualityAssuranceAgent
from backend.tools.google_cse_search import search_google_cse

class NewsFetchAgent:
    _cache = []
    _seen_headlines = set()
    _last_fetch_time = 0
    _cache_ttl = 300  # 5 minutes cache
    _search_semaphore = asyncio.Semaphore(2) # Limit concurrent searches to avoid 400 errors

    def __init__(self):
        # Using 2.0 Flash for high-speed processing
        self.model_name = 'models/gemini-2.0-flash'
        
        # Grounding tool (dynamic retrieval) - Now using DuckDuckGo instead of Google Search
        self.model_with_search = None
        try:
            # We are using Gemini basic model and feeding it DDG search context manually
            # to respect the user's "DuckDuckGo ONLY" constraint.
            self.model_basic = genai.GenerativeModel(self.model_name)
            print(f"[INFO] News Intelligence Agent initialized with {self.model_name}. Grounding via Search Results.")
        except Exception as e:
            print(f"[ERROR] Could not initialize Gemini model: {e}")

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

    async def search_query(self, query: str) -> List[Dict]:
        """Performs a specific search for the user and returns normalized news items."""
        search_results = search_google_cse(query, max_results=10)
        if not search_results:
            return []
            
        context_str = ""
        for res in search_results:
            context_str += f"- Title: {res['title']}\n  Snippet: {res['snippet']}\n  URL: {res['link']}\n\n"

        prompt = f"""
        Analyze these search results for "{query}".
        Extract 5 most relevant, high-quality, and authentic news articles or technical updates.
        
        SEARCH DATA:
        {context_str}
        
        STRICT OUTPUT CONTRACT (JSON ONLY):
        [
            {{
                "headline": "...",
                "summary": "...",
                "domain": "Search Result",
                "source_name": "...",
                "source_url": "...",
                "relevance_score": 0.95
            }}
        ]
        """
        try:
            response = await self.model_basic.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            items = json.loads(text)
            
            # Verify and fix
            tasks = [self.qa_agent.verify_and_fix(item) for item in items]
            cleaned_items = await asyncio.gather(*tasks)
            
            # Link verification
            verified_news = []
            async with aiohttp.ClientSession() as session:
                for item in cleaned_items:
                    if item and item.get("source_url"):
                        if await self.verify_link(session, item["source_url"]):
                            verified_news.append(item)
            return verified_news
        except Exception as e:
            print(f"[ERROR] Search query failed: {e}")
            return []

    async def fetch(self, query=None, force_refresh=False):
        """
        Fetches, analyzes, and returns domain-specific news with strict filtering.
        Mandates REAL search results for all reference links.
        """
        if query:
            print(f"--- SEARCHING FOR: {query} ---")
            results = await self.search_query(query)
            return results
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
                print(f"   [Search] Querying search engines for domains: {batch}")
                sys.stdout.flush()
                
                # Fetch Search context for the batch
                query = " recent news ".join(batch) + " news 2026"
                search_results = search_google_cse(query, max_results=15)
                
                context_str = ""
                for res in search_results:
                    context_str += f"- Title: {res['title']}\n  Summary: {res['snippet']}\n  URL: {res['link']}\n\n"

                prompt = f"""
                You are an elite News Intelligence Agent with real-time access to the following search data.
                
                OBJECTIVE:
                Curate 3-5 distinct, most recent, impactful, and authentic news articles from the last 24-48 hours for each of these domains:
                {batch}
                
                SEARCH DATA:
                {context_str}
                
                CRITICAL AUTHENTICITY RULES:
                1. You MUST use the provided search results above to find REAL articles.
                2. Every item MUST have an actual, verified source_url that was provided in the context.
                3. Do NOT use internal training data or hallucinate URLs.
                4. Extract the URL exactly as provided in the search results.
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
                    # Feed the model the DDG context manually
                    response = await self.model_basic.generate_content_async(prompt)
                    text = response.text.strip()
                except Exception as e:
                    print(f"[ERROR] Gemini generation failed for {batch}: {e}")
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
