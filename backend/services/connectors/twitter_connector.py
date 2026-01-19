"""
Twitter/X API v2 Connector for Social Media Data Ingestion

This module implements the Twitter API v2 Recent Search endpoint with:
- Dynamic query building
- Incremental fetching with since_id
- Rate limit handling
- Comprehensive error handling
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote

import aiohttp
from aiohttp import ClientTimeout

from .base_connector import BaseConnector, UnifiedPost, FetchCursor, Platform, APIError, RateLimitError, AuthenticationError


class TwitterQueryBuilder:
    """Dynamic query builder for Twitter API v2"""

    def __init__(self):
        self.conditions = []

    def add_keywords(self, keywords: List[str], operator: str = "OR") -> 'TwitterQueryBuilder':
        """Add keyword search conditions"""
        if not keywords:
            return self

        if len(keywords) == 1:
            # Escape special characters and quote if contains spaces
            keyword = keywords[0].strip()
            if " " in keyword:
                keyword = f'"{keyword}"'
            self.conditions.append(keyword)
        else:
            # Multiple keywords with OR
            escaped_keywords = []
            for kw in keywords:
                kw = kw.strip()
                if " " in kw:
                    kw = f'"{kw}"'
                escaped_keywords.append(kw)
            self.conditions.append(f"({' OR '.join(escaped_keywords)})")

        return self

    def add_handles(self, handles: List[str], operator: str = "OR") -> 'TwitterQueryBuilder':
        """Add handle-based filtering"""
        if not handles:
            return self

        # Remove @ symbols and create from: conditions
        clean_handles = [h.lstrip('@') for h in handles]
        if len(clean_handles) == 1:
            self.conditions.append(f"from:{clean_handles[0]}")
        else:
            handle_conditions = [f"from:{h}" for h in clean_handles]
            self.conditions.append(f"({' OR '.join(handle_conditions)})")

        return self

    def add_exclude_words(self, words: List[str]) -> 'TwitterQueryBuilder':
        """Add words to exclude"""
        for word in words:
            self.conditions.append(f"-{word}")
        return self

    def add_language_filter(self, lang: str) -> 'TwitterQueryBuilder':
        """Add language filter"""
        if lang:
            self.conditions.append(f"lang:{lang}")
        return self

    def add_date_range(self, since: datetime = None, until: datetime = None) -> 'TwitterQueryBuilder':
        """Add date range filtering"""
        if since:
            self.conditions.append(f"since:{since.strftime('%Y-%m-%d_%H:%M:%S')}_UTC")
        if until:
            self.conditions.append(f"until:{until.strftime('%Y-%m-%d_%H:%M:%S')}_UTC")
        return self

    def add_min_likes(self, min_likes: int) -> 'TwitterQueryBuilder':
        """Add minimum likes filter"""
        if min_likes > 0:
            self.conditions.append(f"min_faves:{min_likes}")
        return self

    def add_min_retweets(self, min_retweets: int) -> 'TwitterQueryBuilder':
        """Add minimum retweets filter"""
        if min_retweets > 0:
            self.conditions.append(f"min_retweets:{min_retweets}")
        return self

    def build(self) -> str:
        """Build the final query string"""
        if not self.conditions:
            raise ValueError("No search conditions specified")

        # Join all conditions with spaces (AND logic)
        query = " ".join(self.conditions)

        # URL encode the query
        return quote(query, safe='')

    def reset(self) -> 'TwitterQueryBuilder':
        """Reset the query builder"""
        self.conditions = []
        return self


class TwitterConnector(BaseConnector):
    """Twitter API v2 connector implementation"""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(Platform.TWITTER, config)
        self.bearer_token = config.get('TWITTER_BEARER_TOKEN')
        self.query_builder = TwitterQueryBuilder()
        self._session = None

    @property
    def required_credentials(self) -> List[str]:
        return ['TWITTER_BEARER_TOKEN']

    async def authenticate(self) -> bool:
        """Authenticate with Twitter API v2 using Bearer token"""
        if not await self.validate_credentials():
            raise AuthenticationError("Twitter credentials not configured")

        # Create aiohttp session for connection pooling
        timeout = ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'Authorization': f'Bearer {self.bearer_token}',
                'User-Agent': 'Simplii-Social-Ingestion/1.0'
            }
        )

        # Test authentication with a simple request
        try:
            async with self._session.get(f"{self.BASE_URL}/tweets/search/recent?query=test&max_results=1") as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Twitter Bearer token")
                elif response.status == 403:
                    raise AuthenticationError("Twitter API access forbidden - check token permissions")
                elif response.status != 200:
                    # For test query, we expect some results or no results, but not other errors
                    response_text = await response.text()
                    self.logger.warning(f"Twitter auth test returned {response.status}: {response_text}")

                self._authenticated = True
                self.logger.info("Twitter API authentication successful")
                return True

        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Failed to connect to Twitter API: {e}")

    async def fetch_posts(
        self,
        query: str,
        cursor: Optional[FetchCursor] = None,
        limit: int = 100
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Fetch posts from Twitter Recent Search API"""

        if not self._authenticated or not self._session:
            raise AuthenticationError("Twitter connector not authenticated")

        # Build API request parameters
        params = {
            'query': query,
            'max_results': min(limit, 100),  # Twitter API limit
            'tweet.fields': 'id,text,author_id,created_at,public_metrics,entities,lang',
            'user.fields': 'id,name,username,verified',
            'expansions': 'author_id',
            'sort_order': 'recency'
        }

        # Add incremental fetching cursor
        if cursor and cursor.last_post_id:
            params['since_id'] = cursor.last_post_id

        # Add pagination token if available in cursor metadata
        if cursor and cursor.metadata.get('next_token'):
            params['next_token'] = cursor.metadata['next_token']

        url = f"{self.BASE_URL}/tweets/search/recent"

        async def _fetch_request():
            async with self._session.get(url, params=params) as response:
                return await self._handle_response(response)

        try:
            data = await self._retry_with_backoff(_fetch_request)
            posts, next_cursor = self._process_response(data, cursor)

            self.logger.info(f"Twitter: Fetched {len(posts)} posts for query: {query}")
            return posts, next_cursor

        except Exception as e:
            self.logger.error(f"Twitter fetch failed for query '{query}': {e}")
            raise

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle Twitter API response and errors"""
        if response.status == 429:
            # Rate limit exceeded
            retry_after = None
            if 'x-rate-limit-reset' in response.headers:
                reset_time = int(response.headers['x-rate-limit-reset'])
                current_time = int(datetime.now(timezone.utc).timestamp())
                retry_after = max(0, reset_time - current_time)

            raise RateLimitError(retry_after)

        elif response.status == 401:
            raise AuthenticationError("Twitter authentication failed")

        elif response.status == 403:
            raise APIError(403, "Twitter API access forbidden")

        elif response.status >= 400:
            error_text = await response.text()
            raise APIError(response.status, f"Twitter API error: {error_text}")

        elif response.status != 200:
            raise APIError(response.status, f"Unexpected Twitter API response: {response.status}")

        return await response.json()

    def _process_response(
        self,
        data: Dict[str, Any],
        original_cursor: Optional[FetchCursor]
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Process Twitter API response into unified posts"""

        posts = []
        next_cursor = None

        # Extract tweets and users
        tweets = data.get('data', [])
        users = {}
        if 'includes' in data and 'users' in data['includes']:
            users = {user['id']: user for user in data['includes']['users']}

        fetched_at = datetime.now(timezone.utc)

        for tweet in tweets:
            try:
                unified_post = self.normalize(tweet, users.get(tweet.get('author_id')))
                unified_post.fetched_at = fetched_at
                posts.append(unified_post)
            except Exception as e:
                self.logger.warning(f"Failed to normalize tweet {tweet.get('id')}: {e}")
                continue

        # Create next cursor for pagination
        if 'meta' in data and 'next_token' in data['meta']:
            next_cursor = FetchCursor(
                platform=Platform.TWITTER.value,
                rule_id=original_cursor.rule_id if original_cursor else "default",
                last_post_id=posts[0].post_id.split(':')[1] if posts else None,
                last_timestamp=fetched_at,
                metadata={'next_token': data['meta']['next_token']}
            )

        return posts, next_cursor

    def normalize(self, tweet: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> UnifiedPost:
        """Normalize Twitter tweet data to UnifiedPost format"""

        tweet_id = tweet['id']
        author_id = tweet.get('author_id', 'unknown')
        created_at_str = tweet['created_at']

        # Parse Twitter timestamp (ISO format)
        try:
            posted_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except ValueError:
            # Fallback for malformed timestamps
            posted_at = datetime.now(timezone.utc)

        # Get author information
        author_name = "Unknown User"
        handle = f"user_{author_id}"

        if user:
            author_name = user.get('name', author_name)
            username = user.get('username', f"user_{author_id}")
            handle = f"@{username}"

        # Extract content and clean it
        content = tweet.get('text', '')
        content = self.sanitize_content(content)

        # Build tweet URL
        username = handle.lstrip('@') if handle.startswith('@') else handle
        url = f"https://twitter.com/{username}/status/{tweet_id}"

        # Create unified post
        return UnifiedPost(
            post_id=self._generate_post_id(tweet_id, Platform.TWITTER.value),
            platform=Platform.TWITTER.value,
            author=author_name,
            handle=handle,
            content=content,
            url=url,
            posted_at=posted_at,
            fetched_at=datetime.now(timezone.utc),
            metadata={
                'tweet_id': tweet_id,
                'author_id': author_id,
                'lang': tweet.get('lang'),
                'public_metrics': tweet.get('public_metrics', {}),
                'entities': tweet.get('entities', {}),
                'verified': user.get('verified', False) if user else False
            }
        )

    def build_query(
        self,
        keywords: Optional[List[str]] = None,
        handles: Optional[List[str]] = None,
        exclude_words: Optional[List[str]] = None,
        language: Optional[str] = None,
        min_likes: int = 0,
        min_retweets: int = 0
    ) -> str:
        """Build a Twitter search query using the query builder"""

        self.query_builder.reset()

        if keywords:
            self.query_builder.add_keywords(keywords)

        if handles:
            self.query_builder.add_handles(handles)

        if exclude_words:
            self.query_builder.add_exclude_words(exclude_words)

        if language:
            self.query_builder.add_language_filter(language)

        if min_likes > 0:
            self.query_builder.add_min_likes(min_likes)

        if min_retweets > 0:
            self.query_builder.add_min_retweets(min_retweets)

        return self.query_builder.build()

    async def close(self):
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None