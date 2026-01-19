"""
Social Media Ingestion API Routes

This module provides API endpoints for managing social media data ingestion,
including running ingestion tasks, monitoring status, and managing rules.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from backend.services.ingestion_service import (
    run_social_ingestion_task,
    run_social_bulk_ingestion_task,
    get_social_ingestion_status
)
from backend.auth.security import get_current_user
from backend.db.models import User


router = APIRouter()


class IngestionRuleRequest(BaseModel):
    """Request model for ingestion rule"""
    rule_id: str = Field(..., description="Unique identifier for the rule")
    platform: str = Field(..., description="Platform to ingest from (twitter, reddit, news)")
    query: str = Field(..., description="Search query for the platform")
    max_posts_per_run: int = Field(100, description="Maximum posts to fetch per run")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional rule metadata")


class BulkIngestionRequest(BaseModel):
    """Request model for bulk ingestion"""
    rules: List[IngestionRuleRequest] = Field(..., description="List of ingestion rules to run")


@router.get("/social-ingestion/status")
async def get_ingestion_status(user: User = Depends(get_current_user)):
    """
    Get the current status of the social ingestion service

    Returns information about available connectors and their authentication status.
    """
    try:
        status = await get_social_ingestion_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion status: {str(e)}")


@router.post("/social-ingestion/run")
async def run_ingestion(
    rule: IngestionRuleRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """
    Run a single social media ingestion task

    This endpoint triggers ingestion for the specified rule and returns immediately.
    The actual ingestion runs in the background.
    """

    # Validate platform
    valid_platforms = ["twitter", "news"]
    if rule.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Supported platforms: {', '.join(valid_platforms)}"
        )

    try:
        # Convert to dict for background task
        rule_dict = rule.dict()

        # Add user context
        rule_dict['user_id'] = user.id
        rule_dict['user_email'] = user.email

        # Run in background
        background_tasks.add_task(run_social_ingestion_task, rule_dict)

        return {
            "message": f"Ingestion started for rule '{rule.rule_id}' on {rule.platform}",
            "rule_id": rule.rule_id,
            "platform": rule.platform,
            "status": "running"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.post("/social-ingestion/run-bulk")
async def run_bulk_ingestion(
    request: BulkIngestionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """
    Run multiple social media ingestion tasks concurrently

    This endpoint triggers bulk ingestion for multiple rules and returns immediately.
    All ingestion tasks run concurrently in the background.
    """

    if not request.rules:
        raise HTTPException(status_code=400, detail="No rules provided")

    # Validate all rules
    valid_platforms = ["twitter", "news"]
    invalid_rules = []

    for rule in request.rules:
        if rule.platform not in valid_platforms:
            invalid_rules.append(f"Rule '{rule.rule_id}': invalid platform '{rule.platform}'")

    if invalid_rules:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rules: {', '.join(invalid_rules)}. Supported platforms: {', '.join(valid_platforms)}"
        )

    try:
        # Convert rules to dicts and add user context
        rules_dicts = []
        for rule in request.rules:
            rule_dict = rule.dict()
            rule_dict['user_id'] = user.id
            rule_dict['user_email'] = user.email
            rules_dicts.append(rule_dict)

        # Run bulk ingestion in background
        background_tasks.add_task(run_social_bulk_ingestion_task, rules_dicts)

        return {
            "message": f"Bulk ingestion started for {len(request.rules)} rules",
            "rules_count": len(request.rules),
            "rule_ids": [rule.rule_id for rule in request.rules],
            "status": "running"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bulk ingestion: {str(e)}")


@router.get("/social-ingestion/platforms")
async def get_available_platforms(user: User = Depends(get_current_user)):
    """
    Get list of available social media platforms

    Returns the platforms that are configured and available for ingestion.
    """
    try:
        status = await get_social_ingestion_status()
        return {
            "platforms": status.get("available_platforms", []),
            "connector_status": status.get("connector_status", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get platforms: {str(e)}")


@router.post("/social-ingestion/test-query")
async def test_query(
    platform: str,
    query: str,
    limit: int = 5,
    user: User = Depends(get_current_user)
):
    """
    Test a query on a specific platform

    This endpoint allows testing queries before creating ingestion rules.
    It fetches a small number of posts to verify the query works.
    """

    valid_platforms = ["twitter", "reddit", "news"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Supported platforms: {', '.join(valid_platforms)}"
        )

    try:
        # Create a test rule
        test_rule = {
            "rule_id": f"test_{platform}_{user.id}",
            "platform": platform,
            "query": query,
            "max_posts_per_run": limit,
            "enabled": True,
            "user_id": user.id,
            "user_email": user.email
        }

        # Run test ingestion
        result = await run_social_ingestion_task(test_rule)

        # Return sample results
        return {
            "platform": platform,
            "query": query,
            "success": "error" not in result,
            "posts_found": result.get("posts_fetched", 0),
            "posts_processed": result.get("posts_processed", 0),
            "errors": result.get("errors", []),
            "duration_seconds": result.get("duration_seconds", 0),
            "sample_data": result.get("rule_config", {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query test failed: {str(e)}")


# Example ingestion rules for different platforms
EXAMPLE_RULES = {
    "twitter_trending_ai": {
        "rule_id": "twitter_ai_trends",
        "platform": "twitter",
        "query": "(artificial intelligence OR AI OR machine learning) -filter:replies",
        "max_posts_per_run": 50,
        "enabled": True
    },
    "news_ai_headlines": {
        "rule_id": "news_ai_today",
        "platform": "news",
        "query": "artificial intelligence",
        "max_posts_per_run": 30,
        "enabled": True
    }
}


@router.get("/social-ingestion/examples")
async def get_example_rules(user: User = Depends(get_current_user)):
    """
    Get example ingestion rules for different platforms

    Returns pre-configured rule examples that can be used as templates.
    """
    return {
        "examples": EXAMPLE_RULES,
        "description": "Example ingestion rules for different platforms. Modify these to create your own rules."
    }


@router.get("/social-ingestion/query-syntax/{platform}")
async def get_query_syntax(platform: str, user: User = Depends(get_current_user)):
    """
    Get query syntax documentation for a specific platform

    Returns information about how to construct queries for the specified platform.
    """

    syntax_docs = {
        "twitter": {
            "description": "Twitter API v2 Recent Search syntax",
            "examples": [
                "AI OR machine learning",
                "(startup OR venture) from:sequoia",
                "artificial intelligence -filter:replies min_faves:10",
                "tech lang:en since:2024-01-01"
            ],
            "operators": [
                "OR - logical OR",
                "AND - logical AND (implied)",
                "NOT or - - exclude terms",
                "from:username - posts from specific user",
                "to:username - posts to specific user",
                "lang:code - filter by language",
                "since:YYYY-MM-DD - posts since date",
                "until:YYYY-MM-DD - posts until date",
                "min_faves:N - minimum likes",
                "min_retweets:N - minimum retweets"
            ]
        },
        "news": {
            "description": "News API search syntax with date filtering",
            "examples": [
                "artificial intelligence",
                "AI source:bbc-news",
                "tech from:2024-01-01 to:2024-01-31"
            ],
            "operators": [
                "source:name - filter by news source",
                "from:YYYY-MM-DD - articles from date",
                "to:YYYY-MM-DD - articles to date"
            ]
        }
    }

    if platform not in syntax_docs:
        raise HTTPException(status_code=404, detail=f"No syntax documentation for platform: {platform}")

    return syntax_docs[platform]