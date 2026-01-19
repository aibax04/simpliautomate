"""
Social Media Ingestion Service

This module provides the main ingestion service that integrates with Simplii's
background task system for automated social media data collection.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .connectors.connector_manager import ConnectorManager, IngestionRule, IngestionResult
from backend.config import Config


logger = logging.getLogger(__name__)


class IngestionService:
    """Service for managing social media data ingestion"""

    def __init__(self):
        self.config = self._load_config()
        self.manager = ConnectorManager(self.config)
        self._initialized = False

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
            # Twitter
            'TWITTER_BEARER_TOKEN': Config.TWITTER_BEARER_TOKEN,

            # News
            'NEWS_PROVIDER': Config.NEWS_PROVIDER or 'newsapi',
            'NEWSAPI_KEY': Config.NEWSAPI_KEY,
            'GNEWS_API_KEY': Config.GNEWS_API_KEY,

            # General settings
            'MAX_CONTENT_LENGTH': 10000,
        }

    async def initialize(self):
        """Initialize the ingestion service"""
        if self._initialized:
            return

        logger.info("Initializing Social Media Ingestion Service...")

        # Authenticate all connectors
        auth_results = await self.manager.authenticate_all()

        successful_auths = sum(1 for success in auth_results.values() if success)
        total_connectors = len(auth_results)

        logger.info(f"Connector authentication: {successful_auths}/{total_connectors} successful")

        if successful_auths == 0:
            logger.warning("No connectors authenticated successfully - ingestion will not work")
        elif successful_auths < total_connectors:
            logger.warning(f"Some connectors failed authentication - check credentials")

        self._initialized = True
        logger.info("Social Media Ingestion Service initialized")

    async def run_ingestion_task(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single ingestion task (called by background worker)

        Args:
            rule_config: Rule configuration dictionary

        Returns:
            Result dictionary with ingestion statistics
        """

        if not self._initialized:
            await self.initialize()

        try:
            # Parse rule configuration
            rule = IngestionRule(
                rule_id=rule_config['rule_id'],
                platform=rule_config['platform'],
                query=rule_config['query'],
                enabled=rule_config.get('enabled', True),
                max_posts_per_run=rule_config.get('max_posts_per_run', 100),
                schedule=rule_config.get('schedule'),
                metadata=rule_config.get('metadata', {})
            )

            logger.info(f"Starting ingestion for rule: {rule.rule_id} on {rule.platform}")

            # Run ingestion
            result = await self.manager.run_ingestion_rule(rule)

            # Convert result to dictionary for JSON serialization
            result_dict = result.to_dict()

            # Add additional metadata
            result_dict.update({
                'rule_config': rule_config,
                'available_platforms': self.manager.get_available_platforms(),
                'connector_status': self.manager.get_connector_status()
            })

            logger.info(f"Ingestion completed for rule {rule.rule_id}: {result.posts_processed} posts")

            return result_dict

        except Exception as e:
            logger.error(f"Ingestion task failed for rule {rule_config.get('rule_id', 'unknown')}: {e}")
            return {
                'error': str(e),
                'rule_id': rule_config.get('rule_id', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': False
            }

    async def run_bulk_ingestion_task(self, rules_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run multiple ingestion tasks concurrently

        Args:
            rules_config: List of rule configuration dictionaries

        Returns:
            List of result dictionaries
        """

        if not self._initialized:
            await self.initialize()

        try:
            # Parse rule configurations
            rules = []
            for rule_config in rules_config:
                rule = IngestionRule(
                    rule_id=rule_config['rule_id'],
                    platform=rule_config['platform'],
                    query=rule_config['query'],
                    enabled=rule_config.get('enabled', True),
                    max_posts_per_run=rule_config.get('max_posts_per_run', 100),
                    schedule=rule_config.get('schedule'),
                    metadata=rule_config.get('metadata', {})
                )
                rules.append(rule)

            logger.info(f"Starting bulk ingestion for {len(rules)} rules")

            # Run bulk ingestion
            results = await self.manager.run_bulk_ingestion(rules)

            # Convert results to dictionaries
            result_dicts = []
            for result in results:
                result_dict = result.to_dict()
                result_dict['success'] = len(result.errors) == 0
                result_dicts.append(result_dict)

            logger.info(f"Bulk ingestion completed: {len(result_dicts)} rules processed")

            return result_dicts

        except Exception as e:
            logger.error(f"Bulk ingestion task failed: {e}")
            return [{
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': False
            }]

    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        if not self._initialized:
            await self.initialize()

        return {
            'initialized': self._initialized,
            'available_platforms': self.manager.get_available_platforms(),
            'connector_status': self.manager.get_connector_status(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    async def clear_cursors(self, platform: Optional[str] = None, rule_id: Optional[str] = None):
        """Clear ingestion cursors (for resetting)"""
        self.manager.clear_cursors(platform, rule_id)
        logger.info(f"Cleared cursors for platform={platform}, rule_id={rule_id}")

    async def shutdown(self):
        """Shutdown the service"""
        logger.info("Shutting down Social Media Ingestion Service...")
        await self.manager.close_all()
        self._initialized = False
        logger.info("Social Media Ingestion Service shutdown complete")


# Global service instance
_ingestion_service = None

async def get_ingestion_service() -> IngestionService:
    """Get or create the global ingestion service instance"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
        await _ingestion_service.initialize()
    return _ingestion_service


# Convenience functions for background tasks
async def run_social_ingestion_task(rule_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to run a single ingestion task
    Used by background workers
    """
    service = await get_ingestion_service()
    return await service.run_ingestion_task(rule_config)


async def run_social_bulk_ingestion_task(rules_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to run bulk ingestion tasks
    Used by background workers
    """
    service = await get_ingestion_service()
    return await service.run_bulk_ingestion_task(rules_config)


async def get_social_ingestion_status() -> Dict[str, Any]:
    """Get ingestion service status"""
    service = await get_ingestion_service()
    return await service.get_service_status()