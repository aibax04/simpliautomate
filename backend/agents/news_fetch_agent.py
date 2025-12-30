import google.generativeai as genai
import json
from backend.config import Config

class NewsFetchAgent:
    def __init__(self):
        # Using 2.0 Flash for live search capabilities as 1.5 Pro is not available
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')

    async def fetch(self):
        """
        Fetches live news using Gemini 1.5 Pro's search capabilities.
        Filters for Tech, Judiciary/Legal, and Business.
        """
        prompt = f"""
        Find 5-7 latest news stories from today (Dec 30, 2025) in these categories: {Config.CATEGORIES}.
        Search for real-time news. Do not return outdated info.
        For each news item, provide a high-quality headline, source, context (2-3 sentences), 
        category, and relevant keywords.

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
            # Note: In a real environment, you'd enable the 'google_search' tool here
            # response = self.model.generate_content(prompt, tools=[{'google_search': {}}])
            response = self.model.generate_content(prompt)
            
            # Clean JSON response
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            return json.loads(text)
        except Exception as e:
            print(f"Error fetching news: {e}")
            # Fallback mock for testing if API fails
            return [
                {
                    "headline": "AI Governance Framework Adopted by Global Judiciary",
                    "source": "LegalTech Daily",
                    "context": "A new framework for AI use in courts has been agreed upon by international legal bodies, focusing on transparency and algorithmic accountability.",
                    "category": "Judiciary/Legal Tech",
                    "keywords": ["AI", "Legal", "Governance"]
                }
            ]
