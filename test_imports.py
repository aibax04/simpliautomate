# Test the correct package name (ddgs)
try:
    from ddgs import DDGS
    print("SUCCESS: from ddgs import DDGS works (correct package)")
except ImportError as e:
    print(f"FAILURE: from ddgs import DDGS failed: {e}")

# Test old package name (should fail - package renamed)
try:
    from duckduckgo_search import DDGS
    print("WARNING: from duckduckgo_search import DDGS still works (old package name)")
except ImportError as e:
    print("EXPECTED: from duckduckgo_search import DDGS failed (package renamed to ddgs)")
