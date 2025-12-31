import asyncio
import google.generativeai as genai
import json
import time
from backend.config import Config
from backend.agents.qa_agent import QualityAssuranceAgent

class NewsFetchAgent:
    _cache = []
    _seen_headlines = set()
    _last_fetch_time = 0
    _cache_ttl = 300  # 5 minutes cache

    def __init__(self):
        # We'll use the available gemini-2.5-flash model
        self.model_name = 'models/gemini-2.5-flash'
        
        # Grounding tool
        self.model_with_search = None
        try:
            self.model_with_search = genai.GenerativeModel(
                model_name=self.model_name,
                tools=[{"google_search_retrieval": {}}]
            )
            print(f"[INFO] Search grounding enabled with {self.model_name}")
        except Exception as e:
            print(f"[WARNING] Could not enable search grounding: {e}")

        self.model_basic = genai.GenerativeModel(self.model_name)
        self.qa_agent = QualityAssuranceAgent()

    async def fetch(self, force_refresh=False):
        """
        Fetches, analyzes, and returns domain-specific news with strict filtering.
        Mandates verified sources and 100% linguistic accuracy.
        Accumulates news in a pool to prevent running out.
        """
        current_time = time.time()
        
        # Return a random subset from cache if available and fresh enough
        if not force_refresh and len(NewsFetchAgent._cache) >= 15 and (current_time - NewsFetchAgent._last_fetch_time < NewsFetchAgent._cache_ttl):
            import random
            items = list(NewsFetchAgent._cache)
            random.shuffle(items)
            return items[:20]

        prompt = f"""
        You are an intelligent, domain-aware news intelligence agent.

        OBJECTIVE:
        Fetch 15-20 high-quality, authentic, and insightful news from late December 2025 related to these domains:
        {Config.CATEGORIES}

        WIDENED THINKING RULES (CRITICAL):
        1. You MUST find news specifically for the requested domains.
        2. Vary the domains in your response. Don't just pick one.
        3. Prioritize impactful, recent updates.
        4. Every news item MUST include a real, direct, clickable source_url starting with https://.
        5. source_name must be the actual, specific publisher.
        
        STRICT OUTPUT CONTRACT (JSON ONLY):
        Return ONLY a JSON list of objects:
        [
            {{
                "headline": "Insightful headline focused on impact",
                "summary": "Detailed summary explaining the specific application, its impact, and why it matters.",
                "domain": "One of {Config.CATEGORIES}",
                "source_name": "Authoritative Publisher Name",
                "source_url": "https://direct-article-url.com/path",
                "relevance_score": 0.95
            }}
        ]

        FAIL-SAFE:
        If no high-quality news exists for a domain, skip it and try another from the list.
        """
        
        try:
            # Try with search grounding first
            try:
                if self.model_with_search:
                    response = await self.model_with_search.generate_content_async(prompt)
                else:
                    response = await self.model_basic.generate_content_async(prompt)
            except Exception as search_e:
                print(f"[WARNING] Search grounding failed: {search_e}")
                response = await self.model_basic.generate_content_async(prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            if not text or text == "[]":
                return NewsFetchAgent._cache if NewsFetchAgent._cache else []
                
            news_items = json.loads(text)
            
            print(f"   [Quality Gate] Verifying {len(news_items)} Fetched News Items...")
            
            # Parallelize verification
            tasks = [self.qa_agent.verify_and_fix(item) for item in news_items]
            cleaned_items = await asyncio.gather(*tasks)
            
            new_verified_news = []
            for clean_item in cleaned_items:
                if not clean_item:
                    continue
                
                headline = clean_item.get("headline", "")
                # Skip if we've already seen this exact headline
                if headline in NewsFetchAgent._seen_headlines:
                    continue

                source_url = clean_item.get("source_url", "")
                has_valid_url = source_url and source_url.startswith("http")
                
                # Check if it matches any of our categories
                item_domain = clean_item.get("domain", "").strip()
                is_valid_domain = any(vd.lower() in item_domain.lower() for vd in Config.CATEGORIES)
                
                is_highly_relevant = clean_item.get("relevance_score", 0) >= 0.70
                
                if has_valid_url and is_valid_domain and is_highly_relevant:
                    new_verified_news.append(clean_item)
                    NewsFetchAgent._seen_headlines.add(headline)
            
            # Add new items to the top of the cache
            NewsFetchAgent._cache = new_verified_news + NewsFetchAgent._cache
            
            # Limit cache size to 200 items to keep it fresh
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
