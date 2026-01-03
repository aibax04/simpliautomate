import logging
from ddgs import DDGS
from typing import List, Dict

logger = logging.getLogger(__name__)

def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for the given query and return a list of results.
    Each result contains: title, snippet, and link.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # text search
            ddgs_gen = ddgs.text(query, max_results=max_results)
            for r in ddgs_gen:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link": r.get("href", "")
                })
        
        logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results")
    except Exception as e:
        logger.error(f"Error searching DuckDuckGo: {e}")
        # Return empty list on failure
    
    return results
