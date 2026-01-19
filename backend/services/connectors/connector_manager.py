"""
Connector Manager for Social Media Data Ingestion

This module provides a unified interface for managing multiple social media connectors,
handling cursor tracking, deduplication, and ingestion workflows.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .base_connector import BaseConnector, UnifiedPost, FetchCursor, Platform, ConnectorError
from .twitter_connector import TwitterConnector
from .news_connector import NewsConnector


@dataclass
class IngestionRule:
    """Rule configuration for data ingestion"""
    rule_id: str
    platform: str
    query: str
    enabled: bool = True
    max_posts_per_run: int = 100
    schedule: Optional[str] = None  # Cron expression or interval
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class IngestionResult:
    """Result of an ingestion run"""
    rule_id: str
    platform: str
    posts_fetched: int
    posts_processed: int
    duplicates_skipped: int
    errors: List[str]
    cursor_updated: bool
    duration_seconds: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'platform': self.platform,
            'posts_fetched': self.posts_fetched,
            'posts_processed': self.posts_processed,
            'duplicates_skipped': self.duplicates_skipped,
            'errors': self.errors,
            'cursor_updated': self.cursor_updated,
            'duration_seconds': self.duration_seconds,
            'timestamp': self.timestamp.isoformat()
        }


class CursorStore:
    """In-memory cursor store (can be extended to use Redis/database)"""

    def __init__(self):
        self._cursors: Dict[str, FetchCursor] = {}
        self.logger = logging.getLogger(__name__)

    def get_cursor(self, platform: str, rule_id: str) -> Optional[FetchCursor]:
        """Get cursor for platform and rule"""
        key = f"{platform}:{rule_id}"
        return self._cursors.get(key)

    def save_cursor(self, cursor: FetchCursor):
        """Save cursor"""
        key = f"{cursor.platform}:{cursor.rule_id}"
        self._cursors[key] = cursor
        self.logger.debug(f"Saved cursor for {key}: {cursor.last_post_id}")

    def clear_cursor(self, platform: str, rule_id: str):
        """Clear cursor"""
        key = f"{platform}:{rule_id}"
        if key in self._cursors:
            del self._cursors[key]
            self.logger.debug(f"Cleared cursor for {key}")


class DeduplicationStore:
    """In-memory deduplication store using post hashes"""

    def __init__(self, max_size: int = 10000):
        self._seen_hashes: set = set()
        self._max_size = max_size
        self.logger = logging.getLogger(__name__)

    def is_duplicate(self, post: UnifiedPost) -> bool:
        """Check if post is duplicate"""
        post_hash = post.generate_hash()

        if post_hash in self._seen_hashes:
            return True

        # Add to seen set
        self._seen_hashes.add(post_hash)

        # Maintain size limit (simple LRU-like behavior)
        if len(self._seen_hashes) > self._max_size:
            # Remove oldest entries (this is a simple implementation)
            self._seen_hashes.pop()

        return False

    def clear(self):
        """Clear all stored hashes"""
        self._seen_hashes.clear()
        self.logger.debug("Cleared deduplication store")


class ConnectorManager:
    """Manager for social media connectors"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize stores
        self.cursor_store = CursorStore()
        self.dedup_store = DeduplicationStore()

        # Initialize connectors
        self.connectors: Dict[str, BaseConnector] = {}
        self._setup_connectors()

    def _setup_connectors(self):
        """Initialize available connectors"""
        connector_classes = {
            Platform.TWITTER.value: TwitterConnector,
            Platform.NEWS.value: NewsConnector,
        }

        for platform_name, connector_class in connector_classes.items():
            try:
                connector = connector_class(self.config)
                self.connectors[platform_name] = connector
                self.logger.info(f"Initialized {platform_name} connector")
            except Exception as e:
                self.logger.warning(f"Failed to initialize {platform_name} connector: {e}")

    async def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate all available connectors"""
        results = {}

        for platform, connector in self.connectors.items():
            try:
                authenticated = await connector.authenticate()
                results[platform] = authenticated
                self.logger.info(f"{platform} connector authentication: {'SUCCESS' if authenticated else 'FAILED'}")
            except Exception as e:
                results[platform] = False
                self.logger.error(f"{platform} connector authentication failed: {e}")

        return results

    async def run_ingestion_rule(self, rule: IngestionRule) -> IngestionResult:
        """Run ingestion for a single rule"""

        start_time = datetime.now(timezone.utc)
        errors = []

        try:
            # Get connector for platform
            connector = self.connectors.get(rule.platform)
            if not connector:
                raise ConnectorError(f"No connector available for platform: {rule.platform}")

            # Get cursor for incremental fetching
            cursor = self.cursor_store.get_cursor(rule.platform, rule.rule_id)

            # Fetch posts
            posts, next_cursor = await connector.fetch_posts(
                query=rule.query,
                cursor=cursor,
                limit=rule.max_posts_per_run
            )

            # Process posts (deduplication)
            processed_posts = []
            duplicates_skipped = 0

            for post in posts:
                if self.dedup_store.is_duplicate(post):
                    duplicates_skipped += 1
                    continue
                processed_posts.append(post)

            # Update cursor if we got results
            cursor_updated = False
            if next_cursor:
                self.cursor_store.save_cursor(next_cursor)
                cursor_updated = True

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = IngestionResult(
                rule_id=rule.rule_id,
                platform=rule.platform,
                posts_fetched=len(posts),
                posts_processed=len(processed_posts),
                duplicates_skipped=duplicates_skipped,
                errors=errors,
                cursor_updated=cursor_updated,
                duration_seconds=duration,
                timestamp=start_time
            )

            self.logger.info(f"Ingestion completed for rule {rule.rule_id}: {len(processed_posts)} posts processed")
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Ingestion failed: {str(e)}"
            errors.append(error_msg)
            self.logger.error(f"Rule {rule.rule_id} ingestion failed: {e}")

            return IngestionResult(
                rule_id=rule.rule_id,
                platform=rule.platform,
                posts_fetched=0,
                posts_processed=0,
                duplicates_skipped=0,
                errors=errors,
                cursor_updated=False,
                duration_seconds=duration,
                timestamp=start_time
            )

    async def run_bulk_ingestion(self, rules: List[IngestionRule]) -> List[IngestionResult]:
        """Run ingestion for multiple rules concurrently"""

        # Filter enabled rules
        enabled_rules = [rule for rule in rules if rule.enabled]

        if not enabled_rules:
            self.logger.info("No enabled rules to process")
            return []

        # Run rules concurrently
        tasks = [self.run_ingestion_rule(rule) for rule in enabled_rules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                rule = enabled_rules[i]
                self.logger.error(f"Rule {rule.rule_id} failed with exception: {result}")
                # Create error result
                error_result = IngestionResult(
                    rule_id=rule.rule_id,
                    platform=rule.platform,
                    posts_fetched=0,
                    posts_processed=0,
                    duplicates_skipped=0,
                    errors=[str(result)],
                    cursor_updated=False,
                    duration_seconds=0.0,
                    timestamp=datetime.now(timezone.utc)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def get_available_platforms(self) -> List[str]:
        """Get list of available platforms"""
        return list(self.connectors.keys())

    def get_connector_status(self) -> Dict[str, bool]:
        """Get authentication status of all connectors"""
        return {platform: connector._authenticated for platform, connector in self.connectors.items()}

    async def close_all(self):
        """Close all connectors"""
        for connector in self.connectors.values():
            try:
                await connector.close()
            except Exception as e:
                self.logger.warning(f"Error closing connector: {e}")

    # Query building utilities
    def build_twitter_query(
        self,
        keywords: Optional[List[str]] = None,
        handles: Optional[List[str]] = None,
        exclude_words: Optional[List[str]] = None,
        language: Optional[str] = None,
        min_likes: int = 0,
        min_retweets: int = 0
    ) -> str:
        """Build Twitter search query"""
        connector = self.connectors.get(Platform.TWITTER.value)
        if isinstance(connector, TwitterConnector):
            return connector.build_query(
                keywords=keywords,
                handles=handles,
                exclude_words=exclude_words,
                language=language,
                min_likes=min_likes,
                min_retweets=min_retweets
            )
        raise ConnectorError("Twitter connector not available")

    def clear_cursors(self, platform: Optional[str] = None, rule_id: Optional[str] = None):
        """Clear cursors (useful for resetting ingestion)"""
        if platform and rule_id:
            self.cursor_store.clear_cursor(platform, rule_id)
        elif platform:
            # Clear all cursors for platform
            keys_to_remove = [k for k in self.cursor_store._cursors.keys() if k.startswith(f"{platform}:")]
            for key in keys_to_remove:
                del self.cursor_store._cursors[key]
        else:
            # Clear all cursors
            self.cursor_store._cursors.clear()

        self.logger.info("Cleared cursors")

    def clear_deduplication_store(self):
        """Clear deduplication store"""
        self.dedup_store.clear()