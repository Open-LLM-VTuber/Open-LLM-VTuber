import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import requests # For requests.exceptions
from utils.web_accessor import WebAccessor, DEFAULT_WEB_ACCESSOR_CONFIG

# Sample HTML content for mocking
SAMPLE_HTML_CONTENT = """
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Main Heading</h1>
    <p>This is a paragraph with some text.</p>
    <p>Another paragraph.</p>
    <script>console.log("script content")</script>
    <style>.heading { font-size: 20px; }</style>
    <section>
        <h2>Subheading</h2>
        <ul><li>Item 1</li><li>Item 2</li></ul>
    </section>
</body>
</html>
"""
EXPECTED_EXTRACTED_TEXT_FROM_SAMPLE_HTML = "Main Heading\nThis is a paragraph with some text.\nAnother paragraph.\nSubheading\nItem 1\nItem 2"


class TestWebAccessor(unittest.TestCase):

    def setUp(self):
        # Use a copy of the default config for each test to avoid modification across tests
        self.base_config = {**DEFAULT_WEB_ACCESSOR_CONFIG, "ENABLED": True}

    @patch('requests.get')
    def test_fetch_url_successful(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        # Use PropertyMock for attributes that are accessed directly
        type(mock_response).content = PropertyMock(return_value=SAMPLE_HTML_CONTENT.encode('utf-8'))
        mock_response.raise_for_status = MagicMock() # Does nothing if status is good
        mock_requests_get.return_value = mock_response

        accessor = WebAccessor(config=self.base_config)
        result = accessor.fetch_url("http://example.com")

        mock_requests_get.assert_called_once_with(
            "http://example.com",
            headers={"User-Agent": self.base_config["USER_AGENT"]},
            timeout=10
        )
        self.assertEqual(result, EXPECTED_EXTRACTED_TEXT_FROM_SAMPLE_HTML)

    @patch('requests.get')
    def test_fetch_url_truncation(self, mock_requests_get):
        long_text = "a" * (DEFAULT_WEB_ACCESSOR_CONFIG["MAX_PAGE_CONTENT_LENGTH"] + 100)
        long_html = f"<html><body><p>{long_text}</p></body></html>"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        type(mock_response).content = PropertyMock(return_value=long_html.encode('utf-8'))
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        config_with_trunc = {**self.base_config, "MAX_PAGE_CONTENT_LENGTH": 50}
        accessor = WebAccessor(config=config_with_trunc)
        result = accessor.fetch_url("http://example.com/long")
        
        self.assertEqual(len(result), 50)
        self.assertTrue(result.startswith("a")) # Check it's the start of the long text

    @patch('requests.get')
    def test_fetch_url_http_error_404(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_requests_get.return_value = mock_response

        accessor = WebAccessor(config=self.base_config)
        result = accessor.fetch_url("http://example.com/notfound")
        
        self.assertTrue(result.startswith("Error: HTTP 404 - Not Found."))

    @patch('requests.get')
    def test_fetch_url_request_exception(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        accessor = WebAccessor(config=self.base_config)
        result = accessor.fetch_url("http://example.com/networkerror")

        self.assertTrue(result.startswith("Error: Could not fetch URL. ConnectionError."))

    @patch('requests.get')
    def test_fetch_url_non_html(self, mock_requests_get):
        plain_text_content = "This is plain text."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        type(mock_response).text = PropertyMock(return_value=plain_text_content) # For non-HTML, .text is used
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        accessor = WebAccessor(config=self.base_config)
        result = accessor.fetch_url("http://example.com/file.txt")
        self.assertEqual(result, plain_text_content)

    def test_fetch_url_disabled(self):
        disabled_config = {**self.base_config, "ENABLED": False}
        accessor = WebAccessor(config=disabled_config)
        result = accessor.fetch_url("http://example.com")
        self.assertEqual(result, "Error: Internet access is disabled in the configuration.")


    @patch('utils.web_accessor.DDGS') # Patch DDGS where it's imported in web_accessor.py
    def test_search_successful(self, mock_ddgs_class):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Result 1", "href": "http://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "http://example.com/2", "body": "Snippet 2"},
        ]
        # DDGS() is a context manager, so mock its __enter__ method to return the instance
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance 

        accessor = WebAccessor(config=self.base_config)
        results = accessor.search("test query")

        mock_ddgs_instance.text.assert_called_once_with("test query", max_results=self.base_config["MAX_SEARCH_RESULTS"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Result 1")
        self.assertEqual(results[1]["url"], "http://example.com/2")

    @patch('utils.web_accessor.DDGS')
    def test_search_limit_param(self, mock_ddgs_class):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [{"title": "R1", "href": "U1", "body": "S1"}] 
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance

        accessor = WebAccessor(config=self.base_config)
        accessor.search("test query", num_results=3)
        
        mock_ddgs_instance.text.assert_called_once_with("test query", max_results=3)

    @patch('utils.web_accessor.DDGS')
    def test_search_limit_config(self, mock_ddgs_class):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance
        
        config_fewer_results = {**self.base_config, "MAX_SEARCH_RESULTS": 2}
        accessor = WebAccessor(config=config_fewer_results)
        accessor.search("test query")

        mock_ddgs_instance.text.assert_called_once_with("test query", max_results=2)

    @patch('utils.web_accessor.DDGS')
    def test_search_api_error(self, mock_ddgs_class):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = Exception("DDGS API Error")
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance

        accessor = WebAccessor(config=self.base_config)
        results = accessor.search("test query")

        self.assertEqual(len(results), 1)
        self.assertTrue("error" in results[0])
        self.assertTrue("DDGS API Error" in results[0]["error"] or "Exception" in results[0]["error"])


    def test_search_disabled(self):
        disabled_config = {**self.base_config, "ENABLED": False}
        accessor = WebAccessor(config=disabled_config)
        results = accessor.search("test query")
        self.assertEqual(len(results), 1)
        self.assertTrue("error" in results[0])
        self.assertEqual(results[0]["error"], "Internet access is disabled in the configuration.")

    @patch('utils.web_accessor.DDGS')
    def test_search_unsupported_engine(self, mock_ddgs_class):
        config_bad_engine = {**self.base_config, "SEARCH_ENGINE_API": "bing"}
        accessor = WebAccessor(config=config_bad_engine)
        results = accessor.search("test query")

        mock_ddgs_class.assert_not_called() # DDGS should not be called
        self.assertEqual(len(results), 1)
        self.assertTrue("error" in results[0])
        self.assertEqual(results[0]["error"], "Unsupported search engine: bing")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
