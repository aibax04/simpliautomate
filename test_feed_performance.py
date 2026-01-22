#!/usr/bin/env python3
"""
Performance Test for Optimized Live Feed API

Tests that the Live Feed API responds in under 500ms as required.
"""

import requests
import time
import json
from datetime import datetime, timedelta

def test_feed_performance(base_url="http://localhost:8001", auth_token=None):
    """Test Live Feed API performance"""

    print("🚀 Testing Live Feed API Performance")
    print("=" * 50)

    headers = {'Content-Type': 'application/json'}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    # Test 1: Basic response time
    print("1. Testing Basic Feed Response Time")
    print("-" * 35)

    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/api/social-listening/feed", headers=headers, timeout=5)
        response_time = time.time() - start_time

        print(f"Status: {response.status_code}")
        print(f"Response Time: {response_time:.3f}s")

        if response.status_code == 401:
            print("⚠️  Authentication required - limited testing")
            return False
        elif response.status_code == 200:
            if response_time < 0.5:
                print("✅ PASS: Response time < 500ms")
                success = True
            else:
                print("❌ FAIL: Response time >= 500ms")
                success = False

            # Check response structure
            data = response.json()
            if 'items' in data and 'performance' in data:
                print("✅ PASS: Correct response structure")
                perf = data['performance']
                print(f"   Query Time: {perf.get('query_time_ms', 'N/A')}ms")
                print(f"   Total Time: {perf.get('total_time_ms', 'N/A')}ms")
                print(f"   Items Returned: {perf.get('item_count', 'N/A')}")
            else:
                print("❌ FAIL: Missing response structure")
                success = False

        else:
            print(f"❌ FAIL: Unexpected status {response.status_code}")
            success = False

    except requests.exceptions.Timeout:
        print("❌ FAIL: Request timed out (>5s)")
        success = False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        success = False

    # Test 2: Different filter combinations
    print("\n2. Testing Filter Performance")
    print("-" * 30)

    filter_tests = [
        {"name": "Time Range (7d)", "params": {"time_range": "7d"}},
        {"name": "Platform Filter", "params": {"platform": "twitter"}},
        {"name": "Sort Order", "params": {"sort_order": "oldest"}},
        {"name": "Combined Filters", "params": {"time_range": "7d", "platform": "news", "sort_order": "newest"}},
        {"name": "Pagination", "params": {"limit": "10", "offset": "0"}},
    ]

    all_filters_pass = True
    for test in filter_tests:
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/api/social-listening/feed",
                                  params=test["params"], headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200 and response_time < 0.5:
                print(f"✅ {test['name']}: {response_time:.3f}s")
            else:
                print(f"❌ {test['name']}: {response_time:.3f}s (status: {response.status_code})")
                all_filters_pass = False

        except Exception as e:
            print(f"❌ {test['name']}: ERROR - {e}")
            all_filters_pass = False

    # Test 3: Load testing simulation
    print("\n3. Load Testing Simulation")
    print("-" * 25)

    print("Simulating 5 concurrent requests...")
    import threading

    results = []
    def make_request():
        try:
            start = time.time()
            response = requests.get(f"{base_url}/api/social-listening/feed",
                                  headers=headers, timeout=10)
            duration = time.time() - start
            results.append((response.status_code, duration))
        except Exception as e:
            results.append((0, 10))  # Timeout/error

    threads = []
    for i in range(5):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    load_pass = True
    total_time = 0
    for status, duration in results:
        total_time += duration
        if status != 200 or duration >= 0.5:
            load_pass = False

    avg_time = total_time / len(results)
    print(f"Average response time: {avg_time:.3f}s")
    if load_pass:
        print("✅ PASS: All concurrent requests < 500ms")
    else:
        print("❌ FAIL: Some concurrent requests failed or were slow")

    # Test 4: Memory usage check (response size)
    print("\n4. Response Size Check")
    print("-" * 20)

    try:
        response = requests.get(f"{base_url}/api/social-listening/feed", headers=headers, timeout=5)
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            print(f"Response Size: {size_kb:.1f} KB")

            if size_kb < 1024:  # < 1MB
                print("✅ PASS: Response size < 1MB")
                size_pass = True
            else:
                print("❌ FAIL: Response size >= 1MB")
                size_pass = False
        else:
            size_pass = False
    except Exception as e:
        print(f"❌ Size check failed: {e}")
        size_pass = False

    # Final Results
    print("\n" + "=" * 50)
    print("FINAL PERFORMANCE RESULTS")
    print("=" * 50)

    overall_success = success and all_filters_pass and load_pass and size_pass

    if overall_success:
        print("🎉 SUCCESS: Live Feed API meets all performance targets!")
        print("\n✅ Performance Targets Met:")
        print("  • Response time < 500ms")
        print("  • All filters work efficiently")
        print("  • Handles concurrent load")
        print("  • Response size < 1MB")
        print("\n🚀 API is production-ready!")
    else:
        print("❌ Some performance targets not met:")
        if not success:
            print("  • Basic response time >= 500ms")
        if not all_filters_pass:
            print("  • Some filters are slow")
        if not load_pass:
            print("  • Cannot handle concurrent requests")
        if not size_pass:
            print("  • Response size too large")

    return overall_success

def test_ingestion_separation():
    """Test that ingestion is properly separated from API calls"""

    print("\n5. Testing Ingestion Separation")
    print("-" * 30)

    try:
        # Test that fetch endpoint returns immediately (not blocking)
        start_time = time.time()
        response = requests.post("http://localhost:8001/api/social-listening/fetch", timeout=10)
        response_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            if "accepted" in data.get("status", ""):
                print("✅ PASS: Fetch endpoint returns immediately")
                print(f"   Response time: {response_time:.3f}s")
                if response_time < 1.0:  # Should return very quickly
                    print("✅ PASS: Non-blocking ingestion")
                    return True
                else:
                    print("❌ FAIL: Fetch endpoint still blocking")
                    return False
            else:
                print("❌ FAIL: Unexpected response structure")
                return False
        else:
            print(f"❌ FAIL: Fetch endpoint error (status: {response.status_code})")
            return False

    except requests.exceptions.Timeout:
        print("❌ FAIL: Fetch endpoint timed out (still blocking)")
        return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

if __name__ == "__main__":
    print("Live Feed Performance Test Suite")
    print("=================================")

    # Run tests
    api_test = test_feed_performance()
    ingestion_test = test_ingestion_separation()

    print("\n" + "=" * 60)
    print("OVERALL TEST RESULTS")
    print("=" * 60)

    if api_test and ingestion_test:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Live Feed API is optimized and production-ready")
        print("✅ 504 Gateway Timeout issue should be resolved")
    else:
        print("❌ Some tests failed")
        print("🔧 Check database indexes and query optimization")

    print("\n📊 Next Steps:")
    print("1. Run: python backend/db/migrate_performance_indexes.py")
    print("2. Restart the server")
    print("3. Test the Live Feed refresh button - should be instant now")