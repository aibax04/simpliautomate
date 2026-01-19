"""
Base Connector Module for Social Media Data Ingestion

This module provides the abstract base class for all social media connectors
in the Simplii platform. All connectors must implement the standardized interface
for authentication, data fetching, and normalization.
"""

import abc
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported social media platforms"""
    TWITTER = "twitter"
    REDDIT = "reddit"
    NEWS = "news"


@dataclass
class UnifiedPost:
    """Unified post schema for all platforms"""
    post_id: str
    platform: str
    author: str
    handle: str
    content: str
    url: str
    posted_at: datetime
    fetched_at: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'post_id': self.post_id,
            'platform': self.platform,
            'author': self.author,
            'handle': self.handle,
            'content': self.content,
            'url': self.url,
            'posted_at': self.posted_at.isoformat(),
            'fetched_at': self.fetched_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedPost':
        """Create from dictionary"""
        return cls(
            post_id=data['post_id'],
            platform=data['platform'],
            author=data['author'],
            handle=data['handle'],
            content=data['content'],
            url=data['url'],
            posted_at=datetime.fromisoformat(data['posted_at']),
            fetched_at=datetime.fromisoformat(data['fetched_at']),
            metadata=data.get('metadata', {})
        )

    def generate_hash(self) -> str:
        """Generate a unique hash for deduplication"""
        content_hash = hashlib.md5(
            f"{self.platform}:{self.post_id}:{self.content}".encode()
        ).hexdigest()
        return content_hash


@dataclass
class FetchCursor:
    """Cursor for incremental fetching"""
    platform: str
    rule_id: str
    last_post_id: Optional[str] = None
    last_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'platform': self.platform,
            'rule_id': self.rule_id,
            'last_post_id': self.last_post_id,
            'last_timestamp': self.last_timestamp.isoformat() if self.last_timestamp else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FetchCursor':
        return cls(
            platform=data['platform'],
            rule_id=data['rule_id'],
            last_post_id=data.get('last_post_id'),
            last_timestamp=datetime.fromisoformat(data['last_timestamp']) if data.get('last_timestamp') else None,
            metadata=data.get('metadata', {})
        )


class ConnectorError(Exception):
    """Base exception for connector errors"""
    pass


class AuthenticationError(ConnectorError):
    """Authentication failed"""
    pass


class RateLimitError(ConnectorError):
    """API rate limit exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after: {retry_after}s")


class APIError(ConnectorError):
    """General API error"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class BaseConnector(abc.ABC):
    """
    Abstract base class for all social media connectors.

    All connectors must implement the following interface:
    - authenticate(): Set up API credentials
    - fetch_posts(): Fetch posts based on query and cursor
    - normalize(): Convert raw API data to UnifiedPost objects
    """

    def __init__(self, platform: Platform, config: Dict[str, Any]):
        self.platform = platform
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{platform.value}")
        self._authenticated = False
        self._client = None

    @property
    @abc.abstractmethod
    def required_credentials(self) -> List[str]:
        """Return list of required environment variable names"""
        pass

    @abc.abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform API.

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abc.abstractmethod
    async def fetch_posts(
        self,
        query: str,
        cursor: Optional[FetchCursor] = None,
        limit: int = 100
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """
        Fetch posts from the platform.

        Args:
            query: Search query (platform-specific format)
            cursor: Cursor for incremental fetching
            limit: Maximum number of posts to fetch

        Returns:
            Tuple of (posts, next_cursor)

        Raises:
            APIError: For API-related errors
            RateLimitError: When rate limited
        """
        pass

    @abc.abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> UnifiedPost:
        """
        Normalize raw API data into UnifiedPost format.

        Args:
            raw_data: Raw data from platform API

        Returns:
            UnifiedPost: Normalized post data

        Raises:
            ValueError: If data cannot be normalized
        """
        pass

    async def validate_credentials(self) -> bool:
        """Validate that required credentials are available"""
        missing = []
        for cred in self.required_credentials:
            if not self.config.get(cred):
                missing.append(cred)

        if missing:
            self.logger.error(f"Missing required credentials: {missing}")
            return False

        return True

    async def _retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        *args,
        **kwargs
    ):
        """Execute function with exponential backoff retry logic"""
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise e

                delay = min(base_delay * (2 ** attempt), max_delay)
                if e.retry_after:
                    delay = min(e.retry_after, max_delay)

                self.logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)

            except APIError as e:
                if e.status_code >= 500:  # Server errors
                    if attempt == max_retries - 1:
                        raise e

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    self.logger.warning(f"Server error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise e  # Client errors don't get retried

            except Exception as e:
                last_exception = e
                if attempt == max_retries - 1:
                    raise e

                delay = min(base_delay * (2 ** attempt), max_delay)
                self.logger.warning(f"Unexpected error, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)

        if last_exception:
            raise last_exception

    def sanitize_content(self, content: str) -> str:
        """Sanitize content to prevent XSS and other issues"""
        if not content:
            return ""

        # Remove null bytes and other control characters
        content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')

        # Limit content length (platform-specific, can be overridden)
        max_length = self.config.get('max_content_length', 10000)
        if len(content) > max_length:
            content = content[:max_length] + "..."

        return content.strip()

    def _generate_post_id(self, platform_id: str, platform: str) -> str:
        """Generate a unique post ID across platforms"""
        return f"{platform}:{platform_id}"