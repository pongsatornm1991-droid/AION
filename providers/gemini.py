import os

from dotenv import load_dotenv
from google import genai

from providers.base import AIProvider


class GeminiProvider(AIProvider):

    def __init__(self):

        # --------------------------------------------------
        # Load environment variables
        # --------------------------------------------------

        load_dotenv()

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. "
                "Add GEMINI_API_KEY=your_api_key "
                "to the .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

    def generate(self, prompt: str) -> str:

        if not prompt or not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty."
            )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        if response is None:
            raise RuntimeError(
                "Gemini returned no response."
            )

        text = getattr(
            response,
            "text",
            None,
        )

        if not text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return text.strip()