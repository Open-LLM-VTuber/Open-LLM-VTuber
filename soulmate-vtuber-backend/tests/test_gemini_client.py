import pytest
from app.services.gemini_client import GeminiClient

def test_generate_response_success(mocker):
    """
    Tests the GeminiClient's behavior on a successful API call
    by mocking the generative AI model's response.
    """
    # Arrange: Mock the response object that genai.generate_content would return
    mock_response = mocker.Mock()
    mock_response.text = "This is a mock Gemini response."

    # Arrange: Patch the 'generate_content' method to return our mock response
    mocker.patch(
        'google.generativeai.GenerativeModel.generate_content',
        return_value=mock_response
    )

    # Act: Instantiate the client and run the method to be tested
    client = GeminiClient(api_key="fake-key-for-testing")
    result = client.generate_response("Hello")

    # Assert: The result should be formatted as expected
    assert result == "[generated] This is a mock Gemini response."

def test_generate_response_failure(mocker):
    """
    Tests the GeminiClient's behavior on a failed API call
    by making the mock raise an exception.
    """
    # Arrange: Patch 'generate_content' to raise an exception
    mocker.patch(
        'google.generativeai.GenerativeModel.generate_content',
        side_effect=Exception("Network Error")
    )

    # Act: Instantiate the client and run the method
    client = GeminiClient(api_key="fake-key-for-testing")
    result = client.generate_response("Hello")

    # Assert: The result should be the formatted error message
    assert result == "[error] API call failed: Network Error"

def test_client_initialization_no_api_key():
    """
    Tests that the client handles a missing API key gracefully.
    """
    # Act: Instantiate the client with a None or placeholder API key
    client = GeminiClient(api_key=None)
    result = client.generate_response("Hello")

    # Assert: The client should return a specific mock response
    assert result == "[mock] Gemini API key not set. This is a mock response."
