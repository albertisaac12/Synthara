import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME


class LLMClient:
    """
    Thin wrapper around the Google Gemini API.
    All agents share a single instance of this class.
    """

    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to the Gemini model and returns the raw text response.
        Raises an informative RuntimeError on failure.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"[LLMClient] Generation failed: {e}") from e
