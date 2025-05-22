import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from loguru import logger
from typing import List, Dict, Optional, Any
import yaml # For the __main__ example

# Default configuration (used if not provided or for __main__ example)
DEFAULT_WEB_ACCESSOR_CONFIG = {
    "ENABLED": True,
    "USER_AGENT": "OpenLLMVTuber/1.0 (https://github.com/t41372/Open-LLM-VTuber)",
    "SEARCH_ENGINE_API": "duckduckgo",
    "GOOGLE_API_KEY": "",
    "GOOGLE_CSE_ID": "",
    "MAX_SEARCH_RESULTS": 5,
    "MAX_PAGE_CONTENT_LENGTH": 2000,
}

class WebAccessor:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the WebAccessor with configuration.

        Args:
            config (Optional[Dict[str, Any]]): A dictionary containing the configuration
                                                for internet access, typically from conf.yaml's
                                                INTERNET_ACCESS section.
        """
        if config is None:
            logger.warning("WebAccessor initialized without specific config, using defaults.")
            self.config = DEFAULT_WEB_ACCESSOR_CONFIG
        else:
            self.config = config
            # Ensure all keys from default are present if some are missing in provided config
            for key, value in DEFAULT_WEB_ACCESSOR_CONFIG.items():
                self.config.setdefault(key, value)

        if not self.config.get("ENABLED", False):
            logger.info("Internet access is disabled in the configuration.")
            # You could raise an error here or just let methods fail if called.
            # For now, methods will check this flag.

    def fetch_url(self, url: str) -> str:
        """
        Fetches the content of a given URL, parses HTML, and extracts readable text.

        Args:
            url (str): The URL to fetch.

        Returns:
            str: The extracted and truncated text content, or an error message string.
        """
        if not self.config.get("ENABLED", False):
            return "Error: Internet access is disabled in the configuration."

        headers = {"User-Agent": self.config.get("USER_AGENT")}
        max_length = self.config.get("MAX_PAGE_CONTENT_LENGTH")

        try:
            logger.info(f"Fetching URL: {url} with User-Agent: {headers['User-Agent']}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                logger.warning(f"Content type for {url} is {content_type}, not HTML. Skipping parsing.")
                # Return raw content if not HTML, truncated
                return response.text[:max_length] if response.text else "Error: Empty content."


            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            # Get text from common readable tags
            texts = []
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section', 'li', 'td', 'th']):
                texts.append(tag.get_text(separator=' ', strip=True))
            
            full_text = "\n".join(texts)
            
            if not full_text.strip():
                logger.warning(f"No readable text content found on {url} after parsing.")
                return "Error: No readable text content found on the page."

            logger.success(f"Successfully fetched and parsed URL: {url}. Original length: {len(full_text)}")
            return full_text[:max_length]

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred while fetching {url}: {e}")
            return f"Error: HTTP {e.response.status_code} - {e.response.reason}."
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error occurred while fetching {url}: {e}")
            return f"Error: Could not fetch URL. {type(e).__name__}."
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching {url}: {e}")
            return f"Error: An unexpected error occurred: {type(e).__name__}."

    def search(self, query: str, num_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Performs a web search using the configured search engine.

        Args:
            query (str): The search query.
            num_results (Optional[int]): The desired number of results. Defaults to
                                         MAX_SEARCH_RESULTS from config.

        Returns:
            List[Dict[str, str]]: A list of search results, each a dictionary with
                                  "title", "url", and "snippet". Returns empty list on error.
        """
        if not self.config.get("ENABLED", False):
            logger.error("Search called but internet access is disabled in configuration.")
            return [{"error": "Internet access is disabled in the configuration."}]
            
        search_engine = self.config.get("SEARCH_ENGINE_API", "duckduckgo")
        max_results = num_results if num_results is not None else self.config.get("MAX_SEARCH_RESULTS")

        logger.info(f"Performing search for '{query}' using {search_engine}, max_results={max_results}")

        results = []
        if search_engine == "duckduckgo":
            try:
                with DDGS() as ddgs: # DDGS client is a context manager
                    ddgs_results = ddgs.text(query, max_results=max_results)
                    if ddgs_results:
                        for r in ddgs_results:
                            results.append({
                                "title": r.get('title', 'No Title'),
                                "url": r.get('href', '#'),
                                "snippet": r.get('body', 'No Snippet')
                            })
                    logger.success(f"DuckDuckGo search for '{query}' returned {len(results)} results.")
            except Exception as e:
                logger.error(f"Error during DuckDuckGo search for '{query}': {e}")
                return [{"error": f"DuckDuckGo search failed: {type(e).__name__}"}]
        # Example for future Google Custom Search
        # elif search_engine == "google_custom_search":
        #     api_key = self.config.get("GOOGLE_API_KEY")
        #     cse_id = self.config.get("GOOGLE_CSE_ID")
        #     if not api_key or not cse_id:
        #         logger.error("Google Custom Search selected, but API key or CSE ID is missing.")
        #         return [{"error": "Google Custom Search API key or CSE ID missing."}]
        #     # Implementation for Google Custom Search would go here
        #     logger.warning("Google Custom Search not yet implemented.")
        #     return [{"error": "Google Custom Search not implemented."}]
        else:
            logger.error(f"Unsupported search engine: {search_engine}")
            return [{"error": f"Unsupported search engine: {search_engine}"}]

        return results

if __name__ == '__main__':
    # This block demonstrates usage and allows for basic testing.
    # It uses a dummy config. In a real application, the config would come from conf.yaml.

    logger.info("Running WebAccessor demo...")

    # Create a dummy conf.yaml for demonstration if it doesn't exist
    # This is just for the __main__ block to run independently for testing.
    dummy_conf_path = "temp_conf_for_web_accessor_demo.yaml"
    try:
        with open(dummy_conf_path, 'r') as f:
            main_config = yaml.safe_load(f)
            accessor_config = main_config.get("INTERNET_ACCESS", DEFAULT_WEB_ACCESSOR_CONFIG)
    except FileNotFoundError:
        logger.warning(f"{dummy_conf_path} not found. Using default web accessor config for demo.")
        accessor_config = DEFAULT_WEB_ACCESSOR_CONFIG
        # Create a dummy conf for next time
        with open(dummy_conf_path, 'w') as f:
            yaml.dump({"INTERNET_ACCESS": DEFAULT_WEB_ACCESSOR_CONFIG}, f)
        logger.info(f"Created {dummy_conf_path} with default settings for future demos.")
    except yaml.YAMLError:
        logger.error(f"Error parsing {dummy_conf_path}. Using default web accessor config for demo.")
        accessor_config = DEFAULT_WEB_ACCESSOR_CONFIG

    web_accessor = WebAccessor(config=accessor_config)

    if not web_accessor.config.get("ENABLED"):
        logger.warning("WebAccessor is disabled in the demo configuration. Demo will be limited.")
    
    # --- Test fetch_url ---
    test_url = "https://example.com" # A simple, reliable URL for testing
    logger.info(f"\n--- Testing fetch_url with {test_url} ---")
    content = web_accessor.fetch_url(test_url)
    if content.startswith("Error:"):
        logger.error(f"Failed to fetch {test_url}: {content}")
    else:
        logger.success(f"Fetched content from {test_url} (first 200 chars):\n{content[:200]}")

    test_url_non_html = "https://raw.githubusercontent.com/t41372/Open-LLM-VTuber/main/README.md"
    logger.info(f"\n--- Testing fetch_url with non-HTML URL: {test_url_non_html} ---")
    content_non_html = web_accessor.fetch_url(test_url_non_html)
    if content_non_html.startswith("Error:"):
        logger.error(f"Failed to fetch {test_url_non_html}: {content_non_html}")
    else:
        logger.success(f"Fetched content from {test_url_non_html} (first 200 chars):\n{content_non_html[:200]}")


    # --- Test search ---
    search_query = "What is the capital of France?"
    logger.info(f"\n--- Testing search with query: '{search_query}' ---")
    search_results = web_accessor.search(search_query, num_results=3)

    if search_results and "error" in search_results[0]:
        logger.error(f"Search failed: {search_results[0]['error']}")
    elif not search_results:
        logger.warning("Search returned no results.")
    else:
        logger.success(f"Search results for '{search_query}':")
        for i, res in enumerate(search_results):
            logger.info(f"  Result {i+1}:")
            logger.info(f"    Title: {res.get('title')}")
            logger.info(f"    URL: {res.get('url')}")
            logger.info(f"    Snippet: {res.get('snippet')[:100]}...") # Display first 100 chars of snippet

    search_query_no_results = "asdfqwertylkjhgfdsazxcvb" # Unlikely to yield results
    logger.info(f"\n--- Testing search with query likely yielding no results: '{search_query_no_results}' ---")
    search_results_no_results = web_accessor.search(search_query_no_results, num_results=3)
    if search_results_no_results and "error" in search_results_no_results[0]:
        logger.error(f"Search failed: {search_results_no_results[0]['error']}")
    elif not search_results_no_results:
        logger.success("Search correctly returned no results as expected.")
    else:
        logger.warning(f"Search for '{search_query_no_results}' unexpectedly returned results: {search_results_no_results}")

    logger.info("\nWebAccessor demo finished.")
    # Consider removing the dummy conf file after demo
    # import os
    # if os.path.exists(dummy_conf_path):
    #     os.remove(dummy_conf_path)
    #     logger.info(f"Removed temporary demo config: {dummy_conf_path}")
