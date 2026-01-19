import logging
import asyncio
from ddgs import DDGS
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def search_duckduckgo(query: str, max_results: int = 10, platform: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for the given query and return a list of results.
    Each result contains: title, snippet, and link.

    Args:
        query: Search query
        max_results: Maximum number of results to return
        platform: Optional platform filter ('twitter', 'news') to also search official APIs
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
                    "link": r.get("href", ""),
                    "source": "duckduckgo"
                })

        logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results")

        # If platform is specified and we have social ingestion available, also search official APIs
        if platform in ['twitter', 'news'] and results:
            try:
                # Import here to avoid circular imports
                from backend.services.ingestion_service import get_ingestion_service

                async def add_api_results():
                    try:
                        ingestion_service = await get_ingestion_service()

                        # Simple keyword extraction from query
                        keywords = query.split()[:3]  # Take first 3 words as keywords

                        rule_config = {
                            "rule_id": f"ddg_api_{platform}_{hash(query)}",
                            "platform": platform,
                            "query": " OR ".join(keywords),
                            "max_posts_per_run": min(max_results // 2, 5),  # Don't overwhelm with API results
                            "enabled": True
                        }

                        api_result = await ingestion_service.run_ingestion_task(rule_config)

                        if api_result.get("success"):
                            for post_data in api_result.get("posts", []):
                                results.append({
                                    "title": post_data.get("content", "")[:100] + "..." if len(post_data.get("content", "")) > 100 else post_data.get("content", ""),
                                    "snippet": post_data.get("content", ""),
                                    "link": post_data.get("url", ""),
                                    "source": f"{platform}_api"
                                })

                        logger.info(f"Added {len(api_result.get('posts', []))} API results for {platform}")

                    except Exception as api_e:
                        logger.warning(f"Failed to get API results for {platform}: {api_e}")

                # Run the async API call in a new event loop
                try:
                    asyncio.run(add_api_results())
                except RuntimeError:
                    # If we're already in an event loop, create a task
                    asyncio.create_task(add_api_results())

            except ImportError:
                logger.debug("Social ingestion service not available, using DuckDuckGo only")
            except Exception as e:
                logger.warning(f"Error adding API results: {e}")

    except Exception as e:
        logger.error(f"Error searching DuckDuckGo: {e}")
        # Return empty list on failure

    return results
