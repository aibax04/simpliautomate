"""
News API Connector for Social Media Data Ingestion

This module implements news article ingestion using NewsAPI and GNews.
Supports keyword search, date filtering, and source attribution.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout
from newsapi import NewsApiClient

from .base_connector import BaseConnector, UnifiedPost, FetchCursor, Platform, APIError, RateLimitError, AuthenticationError


class NewsConnector(BaseConnector):
    """News API connector supporting NewsAPI and GNews"""

    NEWSAPI_BASE_URL = "https://newsapi.org/v2"
    GNEWS_BASE_URL = "https://gnews.io/api/v4"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(Platform.NEWS, config)
        self.provider = config.get('NEWS_PROVIDER', 'newsapi').lower()  # 'newsapi' or 'gnews'
        self.newsapi_key = config.get('NEWSAPI_KEY')
        self.gnews_key = config.get('GNEWS_API_KEY')
        self._newsapi_client = None
        self._session = None

    @property
    def required_credentials(self) -> List[str]:
        if self.provider == 'gnews':
            return ['GNEWS_API_KEY']
        else:  # newsapi
            return ['NEWSAPI_KEY']

    async def authenticate(self) -> bool:
        """Authenticate with news API provider"""
        if not await self.validate_credentials():
            raise AuthenticationError(f"{self.provider.upper()} credentials not configured")

        try:
            if self.provider == 'newsapi':
                # Test NewsAPI connection
                timeout = ClientTimeout(total=30)
                self._session = aiohttp.ClientSession(timeout=timeout)

                test_url = f"{self.NEWSAPI_BASE_URL}/top-headlines"
                params = {
                    'apiKey': self.newsapi_key,
                    'country': 'us',
                    'pageSize': 1
                }

                async with self._session.get(test_url, params=params) as response:
                    if response.status == 401:
                        raise AuthenticationError("Invalid NewsAPI key")
                    elif response.status == 429:
                        raise RateLimitError()
                    elif response.status != 200:
                        error_data = await response.json()
                        raise APIError(response.status, f"NewsAPI error: {error_data}")

            elif self.provider == 'gnews':
                # Test GNews connection
                timeout = ClientTimeout(total=30)
                self._session = aiohttp.ClientSession(timeout=timeout)

                test_url = f"{self.GNEWS_BASE_URL}/top-headlines"
                params = {
                    'token': self.gnews_key,
                    'lang': 'en',
                    'max': 1
                }

                async with self._session.get(test_url, params=params) as response:
                    if response.status == 401 or response.status == 403:
                        raise AuthenticationError("Invalid GNews API key")
                    elif response.status == 429:
                        raise RateLimitError()
                    elif response.status != 200:
                        error_data = await response.json()
                        raise APIError(response.status, f"GNews error: {error_data}")

            self._authenticated = True
            self.logger.info(f"{self.provider.upper()} authentication successful")
            return True

        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Failed to connect to {self.provider.upper()}: {e}")

    async def fetch_posts(
        self,
        query: str,
        cursor: Optional[FetchCursor] = None,
        limit: int = 100
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Fetch news articles"""

        if not self._authenticated or not self._session:
            raise AuthenticationError(f"{self.provider.upper()} connector not authenticated")

        # Parse query parameters
        query_params = self._parse_query(query)

        try:
            if self.provider == 'newsapi':
                posts, next_cursor = await self._fetch_newsapi(query_params, cursor, limit)
            elif self.provider == 'gnews':
                posts, next_cursor = await self._fetch_gnews(query_params, cursor, limit)
            else:
                raise ValueError(f"Unsupported news provider: {self.provider}")

            self.logger.info(f"News ({self.provider}): Fetched {len(posts)} articles for query: {query}")
            return posts, next_cursor

        except Exception as e:
            self.logger.error(f"News fetch failed for query '{query}': {e}")
            raise

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """Parse query string into search parameters

        Supports formats:
        - "artificial intelligence" -> basic keyword search
        - "AI source:bbc-news" -> keyword with source filter
        - "tech from:2024-01-01 to:2024-01-31" -> date range
        """

        params = {'q': query}

        # Parse advanced parameters from query
        query_lower = query.lower()

        # Extract source filter
        if 'source:' in query_lower:
            parts = query.split('source:', 1)
            params['q'] = parts[0].strip()
            source_part = parts[1].split()[0]  # Take first word after source:
            params['sources'] = source_part

        # Extract date range
        if 'from:' in query_lower:
            from_part = query_lower.split('from:')[1].split()[0]
            try:
                from_date = datetime.strptime(from_part, '%Y-%m-%d')
                params['from_date'] = from_date
            except ValueError:
                pass  # Invalid date format, ignore

        if 'to:' in query_lower:
            to_part = query_lower.split('to:')[1].split()[0]
            try:
                to_date = datetime.strptime(to_part, '%Y-%m-%d')
                params['to_date'] = to_date
            except ValueError:
                pass  # Invalid date format, ignore

        # Clean up query by removing parsed parameters
        clean_query = params['q']
        clean_query = clean_query.replace('source:', '').replace('from:', '').replace('to:', '').strip()
        params['q'] = clean_query

        return params

    async def _fetch_newsapi(
        self,
        query_params: Dict[str, Any],
        cursor: Optional[FetchCursor],
        limit: int
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Fetch from NewsAPI"""

        # Build NewsAPI parameters
        params = {
            'apiKey': self.newsapi_key,
            'pageSize': min(limit, 100),  # NewsAPI limit
            'language': 'en'
        }

        if query_params.get('q'):
            params['q'] = query_params['q']

        if query_params.get('sources'):
            params['sources'] = query_params['sources']

        # Date filtering for NewsAPI (last 30 days only)
        if query_params.get('from_date'):
            from_date = query_params['from_date']
            # NewsAPI only supports dates within last 30 days
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            if from_date > thirty_days_ago:
                params['from'] = from_date.strftime('%Y-%m-%d')

        if query_params.get('to_date'):
            to_date = query_params['to_date']
            if to_date > thirty_days_ago:
                params['to'] = to_date.strftime('%Y-%m-%d')

        # Add pagination
        if cursor and cursor.metadata.get('page'):
            params['page'] = cursor.metadata['page'] + 1

        async def _newsapi_request():
            url = f"{self.NEWSAPI_BASE_URL}/everything"
            async with self._session.get(url, params=params) as response:
                return await self._handle_newsapi_response(response)

        data = await self._retry_with_backoff(_newsapi_request)
        return self._process_newsapi_response(data, cursor)

    async def _fetch_gnews(
        self,
        query_params: Dict[str, Any],
        cursor: Optional[FetchCursor],
        limit: int
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Fetch from GNews"""

        # Build GNews parameters
        params = {
            'token': self.gnews_key,
            'lang': 'en',
            'max': min(limit, 100)  # GNews limit
        }

        if query_params.get('q'):
            params['q'] = query_params['q']

        # Date filtering for GNews
        if query_params.get('from_date'):
            params['from'] = query_params['from_date'].strftime('%Y-%m-%d')

        if query_params.get('to_date'):
            params['to'] = query_params['to_date'].strftime('%Y-%m-%d')

        # Add pagination (GNews doesn't have traditional pagination)
        if cursor and cursor.metadata.get('offset'):
            params['offset'] = cursor.metadata['offset']

        async def _gnews_request():
            url = f"{self.GNEWS_BASE_URL}/search"
            async with self._session.get(url, params=params) as response:
                return await self._handle_gnews_response(response)

        data = await self._retry_with_backoff(_gnews_request)
        return self._process_gnews_response(data, cursor)

    async def _handle_newsapi_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle NewsAPI response"""
        if response.status == 429:
            raise RateLimitError()
        elif response.status == 401:
            raise AuthenticationError("Invalid NewsAPI key")
        elif response.status >= 400:
            error_data = await response.json()
            raise APIError(response.status, f"NewsAPI error: {error_data}")
        elif response.status != 200:
            raise APIError(response.status, f"Unexpected NewsAPI response: {response.status}")

        return await response.json()

    async def _handle_gnews_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle GNews response"""
        if response.status == 429:
            raise RateLimitError()
        elif response.status == 401 or response.status == 403:
            raise AuthenticationError("Invalid GNews API key")
        elif response.status >= 400:
            error_data = await response.json()
            raise APIError(response.status, f"GNews error: {error_data}")
        elif response.status != 200:
            raise APIError(response.status, f"Unexpected GNews response: {response.status}")

        return await response.json()

    def _process_newsapi_response(
        self,
        data: Dict[str, Any],
        cursor: Optional[FetchCursor]
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Process NewsAPI response"""

        articles = data.get('articles', [])
        posts = []
        fetched_at = datetime.now(timezone.utc)

        for article in articles:
            try:
                unified_post = self.normalize(article, 'newsapi')
                unified_post.fetched_at = fetched_at
                posts.append(unified_post)
            except Exception as e:
                self.logger.warning(f"Failed to normalize NewsAPI article: {e}")
                continue

        # Create next cursor for pagination
        next_cursor = None
        total_results = data.get('totalResults', 0)
        current_page = cursor.metadata.get('page', 0) if cursor else 0

        if len(posts) > 0 and (current_page + 1) * len(posts) < total_results:
            next_cursor = FetchCursor(
                platform=Platform.NEWS.value,
                rule_id=cursor.rule_id if cursor else "default",
                last_timestamp=fetched_at,
                metadata={'page': current_page + 1}
            )

        return posts, next_cursor

    def _process_gnews_response(
        self,
        data: Dict[str, Any],
        cursor: Optional[FetchCursor]
    ) -> Tuple[List[UnifiedPost], Optional[FetchCursor]]:
        """Process GNews response"""

        articles = data.get('articles', [])
        posts = []
        fetched_at = datetime.now(timezone.utc)

        for article in articles:
            try:
                unified_post = self.normalize(article, 'gnews')
                unified_post.fetched_at = fetched_at
                posts.append(unified_post)
            except Exception as e:
                self.logger.warning(f"Failed to normalize GNews article: {e}")
                continue

        # GNews doesn't provide total count, so we assume more pages if we got max results
        next_cursor = None
        current_offset = cursor.metadata.get('offset', 0) if cursor else 0

        if len(articles) >= 100:  # If we got max results, there might be more
            next_cursor = FetchCursor(
                platform=Platform.NEWS.value,
                rule_id=cursor.rule_id if cursor else "default",
                last_timestamp=fetched_at,
                metadata={'offset': current_offset + 100}
            )

        return posts, next_cursor

    def normalize(self, article: Dict[str, Any], source_api: str) -> UnifiedPost:
        """Normalize news article to UnifiedPost format"""

        # Extract basic information
        title = article.get('title', 'Untitled')
        description = article.get('description', '')
        content = article.get('content', '')

        # Build content from available fields
        full_content = title
        if description:
            full_content += f"\n\n{description}"
        if content:
            full_content += f"\n\n{content}"

        content = self.sanitize_content(full_content)

        # Get author information
        author = article.get('author', 'Unknown Author')
        if not author or author == 'Unknown':
            # Try to extract from source
            source_name = article.get('source', {}).get('name', 'Unknown Source')
            author = source_name

        # Create handle from source
        source_info = article.get('source', {})
        source_name = source_info.get('name', 'Unknown Source')
        handle = f"@{source_name.lower().replace(' ', '_')}"

        # Parse publication date
        published_at_str = article.get('publishedAt') or article.get('published_at')
        if published_at_str:
            try:
                # Handle different date formats
                if source_api == 'gnews':
                    posted_at = datetime.strptime(published_at_str, '%a, %d %b %Y %H:%M:%S %Z')
                else:  # newsapi
                    posted_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%SZ')
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            except ValueError:
                posted_at = datetime.now(timezone.utc)
        else:
            posted_at = datetime.now(timezone.utc)

        # Get article URL
        url = article.get('url', '')

        # Generate unique ID from URL or title
        if url:
            article_id = str(hash(url))  # Use URL hash as ID
        else:
            article_id = str(hash(title + str(posted_at)))

        return UnifiedPost(
            post_id=self._generate_post_id(article_id, Platform.NEWS.value),
            platform=Platform.NEWS.value,
            author=author,
            handle=handle,
            content=content,
            url=url,
            posted_at=posted_at,
            fetched_at=datetime.now(timezone.utc),
            metadata={
                'title': title,
                'description': description,
                'source': source_info,
                'api_source': source_api,
                'url_to_image': article.get('urlToImage') or article.get('image'),
                'article_id': article_id
            }
        )

    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None