# language: python
# filepath: tools/web_search.py
from duckduckgo_search import DDGS
from loguru import logger

def search_web(query: str, max_results: int = 5) -> dict:
    """
    Performs a web search using the duckduckgo_search module.
    Returns a dictionary with the search results.
    """
    # Clean up the query by removing both formats of web_search
    query = query.replace("[web_search]", "").replace("web_search", "").strip()
    
    # Configuration parameters (you can adjust as needed)
    region = "wt-wt"
    safesearch = "moderate"
    
    try:
        logger.info(f"DuckDuckGo search: query='{query}', max_results={max_results}")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, safesearch=safesearch, max_results=max_results))
        if not results:
            logger.warning("DuckDuckGo returned no results")
            return {}
        logger.debug(f"DuckDuckGo raw results: {results}")
        return {"results": results}
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DuckDuckGo Web Search using duckduckgo_search module")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    parser.add_argument("--max_results", type=int, default=5, help="Maximum number of search results to display")
    args = parser.parse_args()

    result = search_web(args.query, max_results=args.max_results)
    
    if result.get("error"):
        print("Search failed:", result["error"])
    else:
        results = result.get("results", [])
        print(f"Displaying up to {args.max_results} results:")
        for i, res in enumerate(results, start=1):
            title = res.get("title", "No title")
            link = res.get("href", "No link")
            snippet = res.get("body", "No snippet")
            print(f"{i}. {title}\n   Link: {link}\n   Snippet: {snippet}\n")