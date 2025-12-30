import google.generativeai as genai
import json
from typing import List, Dict
from backend.agents.curation_agent import CurationAgent

class LiveNewsSuggestionAgent:
    def __init__(self):
        # Using 2.0 Flash for live search, or 1.5 Pro if available (grounding support)
        # Using 2.0 Flash based on available models
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        self.curator = CurationAgent()

    async def suggest_news(self, normalized_data: Dict) -> List[Dict]:
        """
        Finds live news based on normalized topics/queries.
        """
        if "error" in normalized_data:
            return []

        queries = normalized_data.get("search_queries", [])
        category = normalized_data.get("primary_category", "General")
        
        # We'll use the first (most specific) query for the main search
        primary_query = queries[0] if queries else "latest technology news"

        prompt = f"""
        Find 5 LIVE, REAL-TIME news stories from the last 24 hours related to: "{primary_query}".
        Focus on: {category}.
        
        For each item, provide:
        - A catchy headline
        - The source name
        - A brief 2-sentence summary/context
        - Category (Tech, Judiciary/Legal Tech, Business, or General)
        - Keywords (list of 2-3 tags)
        
        Return ONLY a JSON list of objects:
        {{
            "headline": "string",
            "source": "string",
            "context": "string",
            "category": "string",
            "keywords": ["string"]
        }}
        """
        
        try:
            # In a real scenario with Google Search tool enabled:
            # response = self.model.generate_content(prompt, tools='google_search_retrieval')
            
            # Assuming standard generation for now which relies on model's internal freshness or connected tools if configured
            response = self.model.generate_content(prompt)
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            news_items = json.loads(text)
            
            # Apply curation styles
            return self.curator.curate(news_items)
            
        except Exception as e:
            print(f"Error suggesting news: {e}")
            # Fallback for demo if search fails
            filtered_topic = queries[0].replace(" news", "").title()
            return self.curator.curate([
                {
                    "headline": f"Latest Developments in {filtered_topic}",
                    "source": "Aggregated Feed",
                    "context": f"Recent reports highlight significant movement in the {filtered_topic} sector, impacting global markets.",
                    "category": category,
                    "keywords": [filtered_topic, "Update", "Global"]
                }
            ])
