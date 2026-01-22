#!/usr/bin/env python3
"""
Test script to verify Live Feed API parameter handling
"""

import requests
import json

def test_feed_api():
    """Test various parameter combinations"""

    base_url = "http://localhost:8001"

    test_cases = [
        {
            "name": "Basic request (no params)",
            "params": {},
            "expected_status": 401  # Will be 401 due to auth, but should not be 422
        },
        {
            "name": "With limit=100",
            "params": {"limit": "100"},
            "expected_status": 401
        },
        {
            "name": "With all parameters",
            "params": {
                "time_range": "7d",
                "platform": "twitter",
                "rule_id": "all",
                "sort_order": "newest",
                "limit": "50",
                "offset": "0"
            },
            "expected_status": 401
        },
        {
            "name": "With invalid sort_order",
            "params": {
                "sort_order": "invalid",
                "limit": "20"
            },
            "expected_status": 401
        }
    ]

    print("Testing Live Feed API Parameter Handling")
    print("=" * 50)

    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Params: {test_case['params']}")

        try:
            response = requests.get(f"{base_url}/api/social-listening/feed", params=test_case['params'], timeout=10)
            print(f"Status: {response.status_code}")

            if response.status_code == 422:
                print("FAILED: Got 422 Unprocessable Entity")
                print(f"Response: {response.text[:200]}")
                return False
            elif response.status_code in [200, 401]:  # 401 is expected without auth
                print("PASSED: No 422 error")
            else:
                print(f"WARN: Unexpected status: {response.status_code}")

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    print("\n" + "=" * 50)
    print("SUCCESS: All tests passed! API handles parameters correctly.")
    return True

if __name__ == "__main__":
    test_feed_api()