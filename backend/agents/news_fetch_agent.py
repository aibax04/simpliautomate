import asyncio
import google.generativeai as genai
import json
from backend.config import Config
from backend.agents.qa_agent import QualityAssuranceAgent

class NewsFetchAgent:
    def __init__(self):
        # Primary model with search
        self.model_with_search = None
        try:
            self.model_with_search = genai.GenerativeModel(
                model_name='models/gemini-2.0-flash',
                tools=[{"google_search_retrieval": {}}]
            )
            print("[INFO] Search grounding enabled.")
        except Exception as e:
            print(f"[WARNING] Could not enable search grounding: {e}")

        # Fallback model without search (though search is preferred for URLs)
        self.model_basic = genai.GenerativeModel('models/gemini-2.5-flash')
        self.qa_agent = QualityAssuranceAgent()

    async def fetch(self):
        """
        Fetches, analyzes, and returns domain-specific AI news with strict filtering.
        Mandates verified sources and 100% linguistic accuracy.
        """
        
        prompt = f"""
        You are an intelligent, domain-aware news intelligence agent.

        OBJECTIVE:
        Fetch high-quality, authentic, and insightful news from late December 2025 related to:
        - Legal AI
        - Healthcare AI
        - Business / Enterprise AI

        WIDENED THINKING RULES (CRITICAL):
        1. Do NOT rely heavily on a single source or narrow platform. Think broadly and contextually.
        2. You MUST consider news from:
           - Judiciary platforms (courts, legal analysis portals, law journals)
           - Government and regulatory bodies
           - Reputed global and Indian newsrooms
           - Industry reports, enterprise adoption stories
           - Research-backed or policy-driven updates
        3. Include indirect but relevant news:
           - Policy changes enabling AI
           - Court tech pilots
           - Hospital digitization
           - Enterprise AI adoption
        4. Go beyond headlines — prioritize impact, decisions, deployments, and consequences.
        5. Prefer “why this matters” news over generic announcements.
        6. Avoid repetitive coverage of the same platform or publisher.

        SOURCE DIVERSITY RULES:
        1. Ensure variety in sources across the fetched list.
        2. If multiple articles say the same thing, return only the most authoritative one.
        3. Penalize over-reliance on any single publisher.

        AUTHENTICITY & VERIFICATION:
        1. Every news item MUST include a real, direct, clickable source_url starting with https://.
        2. source_name must be the actual publisher.
        3. Never hallucinate URLs. If a valid source URL is missing, discard the article.
        
        STRICT OUTPUT CONTRACT (JSON ONLY):
        Return ONLY a JSON list of objects:
        [
            {{
                "headline": "Insightful headline focused on impact",
                "summary": "Detailed summary explaining the specific AI application, its impact, and why it matters.",
                "domain": "Legal AI | Healthcare AI | Business AI",
                "source_name": "Authoritative Publisher Name",
                "source_url": "https://direct-article-url.com/path",
                "relevance_score": 0.95
            }}
        ]

        FAIL-SAFE:
        If no high-quality, diverse, source-backed news exists, return an empty list [].
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
                return []
                
            news_items = json.loads(text)
            
            # Post-fetch filtering for extra safety and source validation
            valid_domains = ["Legal AI", "Healthcare AI", "Business AI"]
            
            print("   [Quality Gate] Verifying Fetched News Language...")
            
            # Parallelize verification
            tasks = [self.qa_agent.verify_and_fix(item) for item in news_items]
            cleaned_items = await asyncio.gather(*tasks)
            
            verified_news = []
            for clean_item in cleaned_items:
                if not clean_item:
                    print("   [Quality Gate] Discarding item due to language quality failure.")
                    continue
                
                source_url = clean_item.get("source_url", "")
                has_valid_url = source_url and source_url.startswith("http")
                is_valid_domain = clean_item.get("domain") in valid_domains
                is_highly_relevant = clean_item.get("relevance_score", 0) >= 0.8
                
                if has_valid_url and is_valid_domain and is_highly_relevant:
                    verified_news.append(clean_item)
            
            print(f"[DEBUG] Fetched {len(verified_news)} fully validated & proofread news items.")
            return verified_news

        except Exception as e:
            print(f"Error fetching news: {e}")
            return []
