import google.generativeai as genai
from app.core.config import settings

class GeminiClient:
    def __init__(self, api_key: str | None):
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("Warning: GEMINI_API_KEY is not set. Using a mock response.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_response(self, user_prompt: str) -> str:
        if self.model is None:
            return "[mock] Gemini API key not set. This is a mock response."

        try:
            # In a real application, this would involve more complex prompt engineering
            response = self.model.generate_content(user_prompt)
            # Assuming the model can be prompted to return in the format "[emotion] text"
            return f"[generated] {response.text}"
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return f"[error] API call failed"

gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
