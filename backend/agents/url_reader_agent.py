import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from typing import Dict

class URLReaderAgent:
    def __init__(self):
        # Using 2.5 Flash for efficient parsing
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def parse_url(self, url: str) -> Dict:
        """
        Fetches URL content and extracts structured themes.
        """
        text = self._fetch_url_content(url)
        
        if not text:
            return {"error": "Could not fetch content from URL"}
            
        return await self._analyze_text(text)

    def _fetch_url_content(self, url: str) -> str:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return ""

    async def _analyze_text(self, text: str) -> Dict:
        prompt = f"""
        Analyze the following webpage content and extract key metadata for news finding.
        
        WEBPAGE CONTENT (Truncated to first 10k chars):
        {text[:10000]}
        
        EXTRACT THE FOLLOWING:
        1. Key Topics: Main subjects (e.g. "AI Regulation", "Crypto Markets").
        2. Entities: Important companies, people, or courts mentioned.
        3. Jurisdiction: If legal/policy, which country/region?
        4. Sector Relevance: Is this Tech, Legal, or Business?
        
        Return ONLY valid JSON:
        {{
            "topics": ["string"],
            "entities": ["string"],
            "jurisdiction": "string",
            "sector": "string"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(clean_text)
        except Exception as e:
            print(f"Error parsing URL with Gemini: {e}")
            return {"error": str(e)}
