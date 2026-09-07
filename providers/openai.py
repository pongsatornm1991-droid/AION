"""Official OpenAI Responses API provider for AION."""

import os

from dotenv import load_dotenv

from providers.base import AIProvider, retry_transient


class OpenAIProvider(AIProvider):
    """Generate text through OpenAI's native Responses API."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-5"

    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Add a project API key "
                "to the local environment or repository secret."
            )

        self.base_url = (
            os.getenv("OPENAI_BASE_URL", self.DEFAULT_BASE_URL).strip()
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = (
            os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL).strip()
            or self.DEFAULT_MODEL
        )

    @staticmethod
    def _output_text(payload):
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        parts = []
        for item in payload.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") != "output_text":
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    def generate(self, prompt: str) -> str:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty.")

        import requests

        def _call():
            response = requests.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": prompt,
                    "store": False,
                },
                timeout=60,
            )

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            if response.status_code >= 400 or payload.get("error"):
                error = payload.get("error") or {}
                message = (
                    error.get("message")
                    if isinstance(error, dict)
                    else error
                )
                raise RuntimeError(
                    "OpenAI API error: "
                    f"{message or f'HTTP {response.status_code}'}"
                )

            return payload

        payload = retry_transient(_call)
        text = self._output_text(payload)
        if not text:
            raise RuntimeError("OpenAI API returned an empty text response.")
        return text
