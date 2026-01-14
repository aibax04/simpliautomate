try:
    from ddgs import DDGS
    print("SUCCESS: from ddgs import DDGS works")
except ImportError as e:
    print(f"FAILURE: from ddgs import DDGS failed: {e}")

try:
    from duckduckgo_search import DDGS
    print("SUCCESS: from duckduckgo_search import DDGS works")
except ImportError as e:
    print(f"FAILURE: from duckduckgo_search import DDGS failed: {e}")
