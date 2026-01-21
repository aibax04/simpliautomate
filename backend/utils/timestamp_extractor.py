import json
import re
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple, List
import requests
import bs4
from bs4 import BeautifulSoup
import feedparser
from dateutil import parser
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class TimestampExtractor:
    """
    High-accuracy post publication timestamp extraction pipeline.
    Uses a prioritized multi-layer fallback approach:
    1. HTML Metadata
    2. JSON-LD Structured Data
    3. RSS Feeds
    4. Visible DOM Scraping
    5. Gemini LLM Fallback (Last resort)
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        else:
            self.model = None

    async def extract(self, url: str, html_content: Optional[str] = None) -> Dict:
        """
        Main entry point for timestamp extraction.
        Returns a dict with: posted_at (ISO string), source, confidence.
        """
        if not html_content:
            try:
                # Use a realistic user agent
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html_content = response.text
            except Exception as e:
                logger.error(f"Failed to fetch content from {url}: {e}")
                return self._fallback_response("unknown", "none")

        soup = BeautifulSoup(html_content, 'html.parser')

        # Layer 1: HTML Metadata
        dt, source = self._extract_from_metadata(soup)
        if dt:
            return self._success_response(dt, source, "HIGH")

        # Layer 2: JSON-LD Structured Data
        dt, source = self._extract_from_json_ld(soup)
        if dt:
            return self._success_response(dt, source, "HIGH")

        # Layer 3: RSS Feed Fallback
        dt, source = await self._extract_from_rss(url)
        if dt:
            return self._success_response(dt, source, "HIGH")

        # Layer 4: Visible DOM Scraping
        dt, source = self._extract_from_dom(soup)
        if dt:
            return self._success_response(dt, source, "MEDIUM")

        # Layer 5: Gemini Fallback
        if self.model:
            dt, source = await self._extract_from_gemini(html_content, url)
            if dt:
                return self._success_response(dt, source, "LOW")

        return self._fallback_response("unknown", "none")

    def _extract_from_metadata(self, soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[str]]:
        """Layer 1: Extract from HTML Meta Tags"""
        meta_selectors = [
            ("property", "article:published_time"),
            ("property", "og:published_time"),
            ("name", "pubdate"),
            ("name", "date"),
            ("name", "article.published"),
            ("name", "published_at"),
            ("itemprop", "datePublished")
        ]

        for attr, value in meta_selectors:
            meta = soup.find("meta", {attr: value})
            if meta and meta.get("content"):
                dt = self._parse_iso_string(meta["content"])
                if dt:
                    return dt, f"metadata:{value}"
        
        return None, None

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[str]]:
        """Layer 2: Extract from JSON-LD Scripts"""
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Recursively search for datePublished, dateCreated, uploadDate
                dt = self._search_json_ld(data)
                if dt:
                    return dt, "json-ld"
            except (json.JSONDecodeError, TypeError):
                continue
        return None, None

    def _search_json_ld(self, data) -> Optional[datetime]:
        """Helper to recursively find dates in JSON-LD"""
        target_keys = ["datePublished", "dateCreated", "uploadDate"]
        
        if isinstance(data, dict):
            for key in target_keys:
                if key in data and isinstance(data[key], str):
                    dt = self._parse_iso_string(data[key])
                    if dt:
                        return dt
            for value in data.values():
                res = self._search_json_ld(value)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = self._search_json_ld(item)
                if res:
                    return res
        return None

    async def _extract_from_rss(self, url: str) -> Tuple[Optional[datetime], Optional[str]]:
        """Layer 3: Try to find article in domain RSS feed"""
        try:
            domain_match = re.match(r'(https?://[^/]+)', url)
            if not domain_match:
                return None, None
            
            domain = domain_match.group(1)
            # Common RSS paths
            rss_paths = ["/feed", "/rss", "/feed.xml", "/index.xml", "/rss.xml", "/feed/atom"]
            
            for path in rss_paths:
                rss_url = domain + path
                # This could be potentially slow, maybe check robots.txt or limit to known sites
                # Limiting to quick check
                try:
                    feed = feedparser.parse(rss_url)
                    if not feed.entries:
                        continue
                    
                    for entry in feed.entries:
                        if entry.get("link") == url:
                            publish_data = entry.get("published_parsed") or entry.get("updated_parsed")
                            if publish_data:
                                dt = datetime(*publish_data[:6], tzinfo=timezone.utc)
                                return dt, "rss"
                except:
                    continue
        except Exception:
            pass
        return None, None

    def _extract_from_dom(self, soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[str]]:
        """Layer 4: Extract from visible <time> tags and common classes"""
        # Try <time> tags
        time_tags = soup.find_all("time")
        for tag in time_tags:
            # Check datetime attribute
            if tag.get("datetime"):
                dt = self._parse_iso_string(tag["datetime"])
                if dt:
                    return dt, "dom:time_attr"
            # Check visible text
            dt = self._parse_iso_string(tag.text)
            if dt:
                return dt, "dom:time_text"

        # Try common class names
        target_classes = ["published-date", "post-date", "entry-date", "date-published", "timestamp"]
        for cls in target_classes:
            elements = soup.find_all(class_=re.compile(cls, re.I))
            for el in elements:
                text = el.text.strip()
                if text:
                    dt = self._parse_iso_string(text)
                    if dt:
                        return dt, f"dom:class:{cls}"
        
        return None, None

    async def _extract_from_gemini(self, html_content: str, url: str) -> Tuple[Optional[datetime], Optional[str]]:
        """Layer 5: Gemini LLM Fallback"""
        if not self.model:
            return None, None

        # Clean HTML to reduce token usage
        # Extract title and first 2000 chars of body text
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string if soup.title else ""
        text_content = soup.get_text(separator=' ', strip=True)[:3000]

        prompt = f"""You are a high-accuracy data extraction engine. Extract the EXACT posting date and time from the following content metadata and text.
URL: {url}
TITLE: {title}
CONTENT: {text_content}

STRICT RULES:
1. Only return a date if explicitly present in the text or metadata.
2. DO NOT infer or guess the date.
3. If not absolutely certain, return "unknown".
4. If relative dates like "2 hours ago" are found, calculate from CURRENT UTC TIME: {datetime.now(timezone.utc).isoformat()}
5. Return ONLY a JSON object.

TEMPLATE:
{{ "posted_at": "ISO_8601_TIMESTAMP_OR_UNKNOWN" }}
"""
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            resp_text = response.text.strip()
            # Clean JSON if wrapped in code blocks
            if resp_text.startswith("```"):
                resp_text = re.search(r'\{.*\}', resp_text, re.S).group(0)
            
            data = json.loads(resp_text)
            posted_at = data.get("posted_at")
            if posted_at and posted_at != "UNKNOWN":
                dt = self._parse_iso_string(posted_at)
                if dt:
                    return dt, "gemini"
        except Exception as e:
            logger.error(f"Gemini fallback error: {e}")
        
        return None, None

    def _parse_iso_string(self, date_str: str) -> Optional[datetime]:
        """Convert various date strings to normalized UTC datetime"""
        if not date_str or len(date_str) < 5:
            return None
        
        date_str = date_str.strip()
        try:
            # Remove common prefixes
            date_str = re.sub(r'^(Published|Posted|Updated|On)\s*[:\s]*', '', date_str, flags=re.I)
            
            dt = parser.parse(date_str)
            # If no timezone, assume UTC (conservative for SaaS/News)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            # Validate: not in far future
            now = datetime.now(timezone.utc)
            if dt > now + timedelta(days=1):
                return None
            
            return dt
        except Exception:
            return None

    def _success_response(self, dt: datetime, source: str, confidence: str) -> Dict:
        return {
            "posted_at": dt.isoformat(),
            "source": source,
            "confidence": confidence
        }

    def _fallback_response(self, source: str, confidence: str) -> Dict:
        return {
            "posted_at": None,
            "source": source,
            "confidence": confidence
        }

# Singleton instance
_extractor = None

def get_timestamp_extractor():
    global _extractor
    if _extractor is None:
        _extractor = TimestampExtractor()
    return _extractor
