"""
Tests for Base Connector Module
"""

import pytest
from unittest.mock import Mock, patch
import asyncio
from datetime import datetime, timezone

from backend.services.connectors.base_connector import (
    BaseConnector, UnifiedPost, FetchCursor, Platform, APIError, RateLimitError
)


class TestUnifiedPost:
    """Test UnifiedPost data class"""

    def test_unified_post_creation(self):
        """Test creating a UnifiedPost"""
        post = UnifiedPost(
            post_id="test:123",
            platform="twitter",
            author="Test User",
            handle="@testuser",
            content="Test content",
            url="https://twitter.com/test/status/123",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )

        assert post.post_id == "test:123"
        assert post.platform == "twitter"
        assert post.author == "Test User"
        assert post.handle == "@testuser"

    def test_unified_post_to_dict(self):
        """Test converting UnifiedPost to dict"""
        posted_at = datetime.now(timezone.utc)
        fetched_at = datetime.now(timezone.utc)

        post = UnifiedPost(
            post_id="test:123",
            platform="twitter",
            author="Test User",
            handle="@testuser",
            content="Test content",
            url="https://twitter.com/test/status/123",
            posted_at=posted_at,
            fetched_at=fetched_at
        )

        data = post.to_dict()
        assert data['post_id'] == "test:123"
        assert data['platform'] == "twitter"
        assert 'posted_at' in data
        assert 'fetched_at' in data

    def test_unified_post_generate_hash(self):
        """Test hash generation for deduplication"""
        post = UnifiedPost(
            post_id="test:123",
            platform="twitter",
            author="Test User",
            handle="@testuser",
            content="Test content",
            url="https://twitter.com/test/status/123",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )

        hash_value = post.generate_hash()
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hash length

        # Same content should generate same hash
        post2 = UnifiedPost(
            post_id="test:456",
            platform="twitter",
            author="Test User",
            handle="@testuser",
            content="Test content",
            url="https://twitter.com/test/status/456",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )

        assert post.generate_hash() == post2.generate_hash()


class TestFetchCursor:
    """Test FetchCursor data class"""

    def test_fetch_cursor_creation(self):
        """Test creating a FetchCursor"""
        cursor = FetchCursor(
            platform="twitter",
            rule_id="test_rule",
            last_post_id="123",
            last_timestamp=datetime.now(timezone.utc)
        )

        assert cursor.platform == "twitter"
        assert cursor.rule_id == "test_rule"
        assert cursor.last_post_id == "123"

    def test_fetch_cursor_to_dict(self):
        """Test converting FetchCursor to dict"""
        timestamp = datetime.now(timezone.utc)
        cursor = FetchCursor(
            platform="twitter",
            rule_id="test_rule",
            last_post_id="123",
            last_timestamp=timestamp,
            metadata={"page": 1}
        )

        data = cursor.to_dict()
        assert data['platform'] == "twitter"
        assert data['rule_id'] == "test_rule"
        assert data['last_post_id'] == "123"
        assert data['metadata'] == {"page": 1}


class MockConnector(BaseConnector):
    """Mock connector for testing"""

    def __init__(self, config=None):
        super().__init__(Platform.TWITTER, config or {})
        self.required_credentials_value = ['TEST_KEY']

    @property
    def required_credentials(self):
        return self.required_credentials_value

    async def authenticate(self):
        return True

    async def fetch_posts(self, query, cursor=None, limit=100):
        return [], None

    def normalize(self, raw_data):
        return UnifiedPost(
            post_id="test:123",
            platform="twitter",
            author="Test",
            handle="@test",
            content="Test",
            url="https://test.com",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )


class TestBaseConnector:
    """Test BaseConnector functionality"""

    @pytest.fixture
    def mock_connector(self):
        return MockConnector({'TEST_KEY': 'test_value'})

    def test_required_credentials(self, mock_connector):
        """Test required credentials property"""
        assert mock_connector.required_credentials == ['TEST_KEY']

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, mock_connector):
        """Test successful credential validation"""
        assert await mock_connector.validate_credentials() == True

    @pytest.mark.asyncio
    async def test_validate_credentials_missing(self, mock_connector):
        """Test missing credential validation"""
        mock_connector.config = {}  # Remove TEST_KEY
        assert await mock_connector.validate_credentials() == False

    def test_sanitize_content(self, mock_connector):
        """Test content sanitization"""
        # Normal content
        assert mock_connector.sanitize_content("Hello world") == "Hello world"

        # Content with control characters
        dirty_content = "Hello\x00world\x01test"
        clean_content = mock_connector.sanitize_content(dirty_content)
        assert '\x00' not in clean_content
        assert '\x01' not in clean_content

        # Long content
        long_content = "x" * 20000
        sanitized = mock_connector.sanitize_content(long_content)
        assert len(sanitized) <= 10000  # max_content_length
        assert sanitized.endswith("...")

    def test_generate_post_id(self, mock_connector):
        """Test post ID generation"""
        post_id = mock_connector._generate_post_id("123", "twitter")
        assert post_id == "twitter:123"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self, mock_connector):
        """Test successful retry with backoff"""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_connector._retry_with_backoff(success_func, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_rate_limit(self, mock_connector):
        """Test retry with rate limit error"""
        call_count = 0

        async def rate_limit_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError(retry_after=1)
            return "success"

        result = await mock_connector._retry_with_backoff(
            rate_limit_func,
            max_retries=3,
            base_delay=0.1  # Short delay for testing
        )
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_retries(self, mock_connector):
        """Test max retries exceeded"""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise APIError(500, "Server error")

        with pytest.raises(APIError):
            await mock_connector._retry_with_backoff(failing_func, max_retries=2)

        assert call_count == 2