import asyncio
import google.generativeai as genai
import json
from typing import List, Dict
from backend.agents.curation_agent import CurationAgent
from backend.agents.qa_agent import QualityAssuranceAgent

class LiveNewsSuggestionAgent:
    def __init__(self):
        # Using 2.0 Flash with Search Grounding support
        try:
            self.model = genai.GenerativeModel(
                model_name='models/gemini-2.0-flash',
                tools=[{"google_search_retrieval": {}}]
            )
            self.search_enabled = True
        except:
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.search_enabled = False
            
        self.curator = CurationAgent()
        self.qa_agent = QualityAssuranceAgent()

    async def suggest_news(self, normalized_data: Dict) -> List[Dict]:
        """
        Finds live news based on normalized topics/queries.
        CRITICAL: Mandates verified sources and 100% spelling/grammar accuracy.
        """
        if "error" in normalized_data:
            return []

        queries = normalized_data.get("search_queries", [])
        category = normalized_data.get("primary_category", "General")
        primary_query = queries[0] if queries else "latest news"

        prompt = f"""
        You are an intelligent, domain-aware news intelligence agent.
        
        OBJECTIVE:
        Find 5 LIVE, HIGH-QUALITY news stories from the last 24 hours related to this topic: "{primary_query}".
        Focus Category: {category}.
        
        WIDENED THINKING RULES (CRITICAL):
        1. Do NOT rely heavily on a single source or narrow platform. Think broadly and contextually.
        2. You MUST consider news from:
           - Judiciary platforms (courts, legal analysis portals, law journals)
           - Government and regulatory bodies
           - Reputed global and Indian newsrooms
           - Industry reports, enterprise adoption stories
           - Research-backed or policy-driven updates
        3. Include indirect but relevant news (e.g., policy changes, tech pilots, digitization, enterprise adoption).
        4. Go beyond headlines — prioritize impact, decisions, deployments, and consequences.
        5. Prefer “why this matters” news over generic announcements.

        AUTHENTICITY & VERIFICATION:
        1. Every news item MUST include a real, direct, clickable source_url starting with https://.
        2. source_name must be the actual publisher.
        3. Never hallucinate URLs. If a valid source URL is missing, discard the article.

        STRICT OUTPUT CONTRACT (JSON ONLY):
        Return ONLY a JSON list of objects:
        [
            {{
                "headline": "Insightful headline focused on impact",
                "source_name": "Authoritative Publisher Name",
                "source_url": "https://direct-article-url.com/path",
                "summary": "Detailed summary explaining the application, impact, and why it matters.",
                "domain": "Legal AI | Healthcare AI | Business AI"
            }}
        ]
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            news_items = json.loads(text)
            
            # QUALITY GATE: Perform spelling and grammar pass on headlines and summaries
            print("   [Quality Gate] Verifying Suggestion Language...")
            
            # Parallelize verification
            tasks = [self.qa_agent.verify_and_fix(item) for item in news_items]
            cleaned_items = await asyncio.gather(*tasks)
            
            verified_items = []
            for verified_item in cleaned_items:
                if not verified_item:
                    continue
                    
                # Validation checklist
                source_url = verified_item.get("source_url", "")
                if source_url and source_url.startswith("http"):
                    verified_items.append(verified_item)
            
            # Apply curation styles
            return self.curator.curate(verified_items)
            
        except Exception as e:
            print(f"Error suggesting news: {e}")
            return []
