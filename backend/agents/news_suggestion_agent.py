import asyncio
import google.generativeai as genai
import json
import aiohttp
from typing import List, Dict
from backend.agents.curation_agent import CurationAgent
from backend.agents.qa_agent import QualityAssuranceAgent

class LiveNewsSuggestionAgent:
    _search_semaphore = asyncio.Semaphore(2)

    def __init__(self):
        # Using 2.0 Flash with Search Grounding support
        try:
            self.model = genai.GenerativeModel(
                model_name='models/gemini-2.0-flash',
                tools=[{"google_search_retrieval": {}}]
            )
            self.search_enabled = True
            print(f"[INFO] Actual Google Search grounding enabled for suggestions")
        except:
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.search_enabled = False
            
        self.curator = CurationAgent()
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

    async def suggest_news(self, normalized_data: Dict) -> List[Dict]:
        """
        Finds live news based on normalized topics/queries using actual Google Search results.
        """
        if "error" in normalized_data:
            return []

        queries = normalized_data.get("search_queries", [])
        category = normalized_data.get("primary_category", "General")
        primary_query = queries[0] if queries else "latest news"

        prompt = f"""
        You are an elite News Intelligence Agent with real-time Google Search access.
        
        OBJECTIVE:
        Find 5 LIVE, AUTHENTIC news stories from the last 24-48 hours related to this topic: "{primary_query}".
        Focus Category: {category}.
        
        CRITICAL AUTHENTICITY RULES:
        1. You MUST use the provided Google Search tool to find REAL articles.
        2. Every item MUST have an actual, verified source_url that you found in the search results.
        3. Do NOT hallucinate URLs or use internal memory for links.
        4. Extract the URL exactly as provided in the search result citations. Do NOT modify it.
        5. source_name must be the actual publisher.
        6. Prefer “why this matters” news over generic announcements.

        STRICT OUTPUT CONTRACT (JSON ONLY):
        Return ONLY a JSON list of objects:
        [
            {{
                "headline": "Authentic headline from search results",
                "source_name": "Actual Publisher",
                "source_url": "https://actual-verified-link.com",
                "summary": "Detailed summary explaining the application, impact, and why it matters.",
                "domain": "{category}"
            }}
        ]
        """
        
        try:
            async with LiveNewsSuggestionAgent._search_semaphore:
                try:
                    # Attempt with search tool
                    response = await self.model.generate_content_async(prompt)
                    text = response.text.strip()
                except Exception as search_e:
                    print(f"[WARNING] Suggestion search tool failed, falling back to basic: {search_e}")
                    # Create a temporary model without the tool for fallback
                    fallback_model = genai.GenerativeModel('models/gemini-2.0-flash')
                    response = await fallback_model.generate_content_async(prompt)
                    text = response.text.strip()
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            news_items = json.loads(text)
            
            # QUALITY GATE: Perform spelling and grammar pass
            print("   [Quality Gate] Verifying Suggestion Language...")
            tasks = [self.qa_agent.verify_and_fix(item) for item in news_items]
            cleaned_items = await asyncio.gather(*tasks)
            
            # LINK VERIFICATION using shared session
            print(f"   [Verification] Checking {len(cleaned_items)} suggestion links...")
            async with aiohttp.ClientSession() as session:
                link_tasks = []
                for item in cleaned_items:
                    if item and item.get("source_url"):
                        link_tasks.append(self.verify_link(session, item["source_url"]))
                    else:
                        link_tasks.append(asyncio.sleep(0, result=False))
                
                link_status = await asyncio.gather(*link_tasks)

            verified_items = []
            for i, verified_item in enumerate(cleaned_items):
                if not verified_item or not link_status[i]:
                    continue
                    
                source_url = verified_item.get("source_url", "")
                if source_url and source_url.startswith("http"):
                    verified_items.append(verified_item)
            
            return self.curator.curate(verified_items)
            
        except Exception as e:
            print(f"Error suggesting news: {e}")
            return []
