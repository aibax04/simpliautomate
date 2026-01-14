from ddgs import DDGS
import json

def test():
    print("Testing DDG...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text("AI news 2026", max_results=5))
            print(f"Count: {len(results)}")
            print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
