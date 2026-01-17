import requests
import os
import logging
from typing import List, Dict
from ddgs import DDGS

logger = logging.getLogger(__name__)

def search_ddg(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Fallback search using DuckDuckGo.
    """
    logger.info(f"Attempting DuckDuckGo fallback for query: '{query}'")
    results = []
    try:
        with DDGS() as ddgs:
            # text search
            ddg_results = ddgs.text(query, max_results=max_results)
            for r in ddg_results:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link": r.get("href", ""),
                    "displayLink": r.get("href", "").split("//")[-1].split("/")[0] if r.get("href") else "duckduckgo.com"
                })
        logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results")
    except Exception as e:
        logger.error(f"Error searching DuckDuckGo: {e}")
    
    return results

def search_google_cse(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search Google Custom Search Engine for the given query.
    Falls back to DuckDuckGo if Google fails (e.g. rate limit).
    """
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        # logger.warning("GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID not set. Falling back to DuckDuckGo.")
        return search_ddg(query, max_results)

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cse_id,
        "num": max_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # If we hit rate limit (429) or Bad Request (400 - likely invalid key), fallback
        if response.status_code in [400, 429]:
            logger.warning(f"Google CSE returned status {response.status_code}. Switching to DuckDuckGo.")
            return search_ddg(query, max_results)
            
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
                "displayLink": item.get("displayLink", "")
            })
        
        logger.info(f"Google CSE search for '{query}' returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Google CSE search failed: {e}. Attempting DuckDuckGo fallback.")
        return search_ddg(query, max_results)
