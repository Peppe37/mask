from duckduckgo_search import DDGS
import json

def test_search():
    print("Testing DDGS...")
    ddgs = DDGS()
    
    query = "python programming language"
    print(f"Searching for: {query}")
    
    try:
        results = list(ddgs.text(query, max_results=3))
        print(f"Found {len(results)} results:")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
