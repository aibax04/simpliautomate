#!/usr/bin/env python3
"""
Social Media Ingestion API Test Script

This script tests the social media ingestion endpoints and demonstrates
how to use the ingestion API.

Usage:
    python test_social_ingestion.py

Requirements:
    - Running Simplii server on localhost:8000 (or configured port)
    - Valid authentication token
    - Configured API credentials in environment
"""

import asyncio
import json
import os
from typing import Dict, Any
import aiohttp
from aiohttp import ClientTimeout


class SocialIngestionTester:
    """Test class for social media ingestion API"""

    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token or os.getenv('SIMPLII_TEST_TOKEN')
        self.session = None

    async def __aenter__(self):
        timeout = ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers

    async def test_status_endpoint(self) -> Dict[str, Any]:
        """Test the status endpoint"""
        print("🔍 Testing /api/social-ingestion/status...")

        url = f"{self.base_url}/api/social-ingestion/status"
        async with self.session.get(url, headers=self._get_headers()) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Status endpoint working")
                print(f"   Available platforms: {result.get('available_platforms', [])}")
                print(f"   Initialized: {result.get('initialized', False)}")
            else:
                print(f"❌ Status endpoint failed: {response.status}")

            return result

    async def test_platforms_endpoint(self) -> Dict[str, Any]:
        """Test the platforms endpoint"""
        print("🔍 Testing /api/social-ingestion/platforms...")

        url = f"{self.base_url}/api/social-ingestion/platforms"
        async with self.session.get(url, headers=self._get_headers()) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Platforms endpoint working")
                platforms = result.get('platforms', [])
                connector_status = result.get('connector_status', {})

                print(f"   Platforms: {platforms}")
                for platform, status in connector_status.items():
                    status_icon = "✅" if status else "❌"
                    print(f"   {platform}: {status_icon}")
            else:
                print(f"❌ Platforms endpoint failed: {response.status}")

            return result

    async def test_query_syntax_endpoint(self) -> Dict[str, Any]:
        """Test the query syntax endpoint"""
        print("🔍 Testing /api/social-ingestion/query-syntax/twitter...")

        url = f"{self.base_url}/api/social-ingestion/query-syntax/twitter"
        async with self.session.get(url, headers=self._get_headers()) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Query syntax endpoint working")
                print(f"   Description: {result.get('description', 'N/A')}")
                examples = result.get('examples', [])
                print(f"   Examples: {examples[:2]}...")  # Show first 2 examples
            else:
                print(f"❌ Query syntax endpoint failed: {response.status}")

            return result

    async def test_example_rules_endpoint(self) -> Dict[str, Any]:
        """Test the example rules endpoint"""
        print("🔍 Testing /api/social-ingestion/examples...")

        url = f"{self.base_url}/api/social-ingestion/examples"
        async with self.session.get(url, headers=self._get_headers()) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Example rules endpoint working")
                examples = result.get('examples', {})
                print(f"   Available examples: {list(examples.keys())}")
            else:
                print(f"❌ Example rules endpoint failed: {response.status}")

            return result

    async def test_run_ingestion(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test running an ingestion task"""
        print(f"🔍 Testing ingestion run for rule: {rule_config.get('rule_id')}...")

        url = f"{self.base_url}/api/social-ingestion/run"
        async with self.session.post(
            url,
            headers=self._get_headers(),
            json=rule_config
        ) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Ingestion task started successfully")
                print(f"   Rule ID: {result.get('rule_id')}")
                print(f"   Platform: {result.get('platform')}")
                print(f"   Status: {result.get('status')}")
            else:
                print(f"❌ Ingestion run failed: {response.status}")
                print(f"   Error: {result}")

            return result

    async def test_query_test(self, platform: str, query: str, limit: int = 3) -> Dict[str, Any]:
        """Test query testing endpoint"""
        print(f"🔍 Testing query on {platform}: '{query}'...")

        url = f"{self.base_url}/api/social-ingestion/test-query"
        params = {
            'platform': platform,
            'query': query,
            'limit': limit
        }

        async with self.session.post(
            url,
            headers=self._get_headers(),
            json=params
        ) as response:
            result = await response.json()

            if response.status == 200:
                print("✅ Query test completed")
                print(f"   Platform: {result.get('platform')}")
                print(f"   Query: {result.get('query')}")
                print(f"   Success: {result.get('success')}")
                print(f"   Posts found: {result.get('posts_found', 0)}")
                if result.get('errors'):
                    print(f"   Errors: {result.get('errors')}")
            else:
                print(f"❌ Query test failed: {response.status}")
                print(f"   Error: {result}")

            return result


async def main():
    """Main test function"""

    print("🚀 Social Media Ingestion API Test Suite")
    print("=" * 50)

    # Get configuration from environment
    base_url = os.getenv('SIMPLII_BASE_URL', 'http://localhost:8000')
    auth_token = os.getenv('SIMPLII_AUTH_TOKEN')

    if not auth_token:
        print("⚠️  Warning: No SIMPLII_AUTH_TOKEN set. Some tests may fail.")
        print("   Set SIMPLII_AUTH_TOKEN environment variable with a valid JWT token")
        print()

    async with SocialIngestionTester(base_url, auth_token) as tester:
        # Test basic endpoints
        await tester.test_status_endpoint()
        print()

        await tester.test_platforms_endpoint()
        print()

        await tester.test_query_syntax_endpoint()
        print()

        await tester.test_example_rules_endpoint()
        print()

        # Test query validation (if credentials are configured)
        print("🔍 Testing sample queries...")

        # Twitter test
        try:
            await tester.test_query_test('twitter', 'AI OR artificial intelligence', 2)
            print()
        except Exception as e:
            print(f"❌ Twitter query test failed: {e}")
            print()


        # News test
        try:
            await tester.test_query_test('news', 'artificial intelligence', 2)
            print()
        except Exception as e:
            print(f"❌ News query test failed: {e}")
            print()

        print("🏁 Test suite completed!")
        print("\n📝 Notes:")
        print("- Make sure your .env file has the required API credentials")
        print("- For Twitter: TWITTER_BEARER_TOKEN")
        print("- For Reddit: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET")
        print("- For News: NEWSAPI_KEY or GNEWS_API_KEY")
        print("\n📖 See README.md for detailed setup instructions")


if __name__ == "__main__":
    asyncio.run(main())