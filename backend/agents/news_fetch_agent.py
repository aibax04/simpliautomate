import google.generativeai as genai
import json
from backend.config import Config

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

        # Fallback model without search
        self.model_basic = genai.GenerativeModel('models/gemini-2.0-flash')

    async def fetch(self):
        """
        Fetches, analyzes, and returns domain-specific AI news with strict filtering.
        Targets: Legal AI, Healthcare AI, and Business AI.
        """
        
        prompt = f"""
        Fetch and analyze the latest news articles from late December 2025 that strictly match the following domains and sub-keywords:

        PRIMARY DOMAINS:
        1. Legal AI: (keywords: legal ai, judicial ai, nyay ai, nyayai, ai in courts, ai for legal research, ai judgement analysis, legaltech ai)
        2. Healthcare AI: (keywords: healthcare ai, medical ai, ai diagnosis, ai radiology, ai drug discovery)
        3. Business AI: (keywords: enterprise ai, ai automation, ai startups, ai saas)

        STRICT FILTERING RULES:
        1. An article MUST explicitly mention at least ONE sub-keyword.
        2. If AI is mentioned but NOT in legal, healthcare, or business context → DISCARD it.
        3. IGNORE political, sports, entertainment, or generic world news.
        4. PREFER judiciary decisions, court rulings, enterprise adoption, hospital usage, or regulatory updates.
        5. If relevance confidence for the specific domain is < 0.7 → DISCARD the article.
        6. Return REAL-TIME news or most recent significant updates.

        OUTPUT REQUIREMENTS:
        - Return only relevant articles.
        - Precision is more important than quantity. Use a conservative approach.
        - Do not hallucinate sources.
        - Categorize each article under its PRIMARY DOMAIN.
        - If no relevant news exists, return an empty list: [].

        Return ONLY a JSON list of objects:
        [
            {{
                "headline": "Strictly relevant headline",
                "source": "Verified news source",
                "context": "2-3 sentences explaining the specific AI application and its impact in the domain.",
                "category": "Legal AI | Healthcare AI | Business AI",
                "keywords": ["specific", "matched", "keywords"],
                "relevance_score": 0.95
            }}
        ]
        """
        
        try:
            # Try with search grounding first
            try:
                if self.model_with_search:
                    response = self.model_with_search.generate_content(prompt)
                else:
                    response = self.model_basic.generate_content(prompt)
            except Exception as search_e:
                print(f"[WARNING] Search grounding failed (likely permission or API limit): {search_e}")
                response = self.model_basic.generate_content(prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            if not text or text == "[]":
                return []
                
            news_items = json.loads(text)
            
            # Post-fetch filtering for extra safety
            valid_domains = ["Legal AI", "Healthcare AI", "Business AI"]
            final_news = [
                item for item in news_items 
                if item.get("category") in valid_domains and item.get("relevance_score", 0) >= 0.7
            ]
            
            print(f"[DEBUG] Fetched {len(final_news)} strictly relevant news items.")
            return final_news

        except Exception as e:
            print(f"Error fetching news: {e}")
            return []
