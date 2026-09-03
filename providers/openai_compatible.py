"""Provider for OpenAI-compatible chat-completions endpoints.

OpenChat can expose this protocol when it is self-hosted, and the same
adapter also works with a private gateway or another compatible service.
Keeping it behind the AIProvider interface means AION's memory, safety gates,
and social cycles stay exactly the same no matter which writing model is used.
"""

import os

from dotenv import load_dotenv

from providers.base import AIProvider, retry_transient


class OpenAICompatibleProvider(AIProvider):
    """Generate text through a configured OpenAI-compatible endpoint."""

    def __init__(self):
        load_dotenv()

        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip()
        if not base_url:
            raise RuntimeError(
                "OPENAI_COMPATIBLE_BASE_URL is not configured. Add the URL "
                "of the OpenAI-compatible /v1 endpoint to .env."
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_COMPATIBLE_MODEL", "openchat_3.6").strip()

        if not self.model:
            raise RuntimeError("OPENAI_COMPATIBLE_MODEL cannot be empty.")

    def generate(self, prompt: str) -> str:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty.")

        import requests

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        def _call():
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
                timeout=45,
            )

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            if response.status_code >= 400 or payload.get("error"):
                error = payload.get("error") or {}
                message = error.get("message") if isinstance(error, dict) else error
                raise RuntimeError(
                    "OpenAI-compatible API error: "
                    f"{message or f'HTTP {response.status_code}'}"
                )

            return payload

        payload = retry_transient(_call)

        choices = payload.get("choices") or []
        message = choices[0].get("message") if choices else None
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenAI-compatible API returned an empty response.")

        return text.strip()
