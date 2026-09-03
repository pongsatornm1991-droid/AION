import os

from dotenv import load_dotenv

from providers.base import AIProvider, retry_transient


class ClaudeProvider(AIProvider):
    """AION provider backed by the Anthropic Claude API.

    Mirrors GeminiProvider's contract exactly (same __init__/generate
    shape, same style of error messages) so the rest of AION never
    needs to know which provider is active. The `anthropic` package
    is imported lazily inside __init__, not at module load time, so
    importing this module (and therefore main.py) never fails just
    because `anthropic` is not installed -- only actually using
    ClaudeProvider requires it, the same rule already applied to
    GeminiProvider/google-genai.
    """

    def __init__(self):

        load_dotenv()

        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not configured. "
                "Add ANTHROPIC_API_KEY=your_api_key "
                "to the .env file."
            )

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        self.client = Anthropic(api_key=api_key)

        # NOTE: verify the current model id against
        # https://docs.claude.com/en/docs/about-claude/models
        # before relying on this default in production -- model
        # ids are periodically retired.
        self.model = os.getenv(
            "ANTHROPIC_MODEL",
            "claude-sonnet-4-5-20250929",
        )

    def generate(self, prompt: str) -> str:

        if not prompt or not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty."
            )

        response = retry_transient(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
        )

        if response is None or not getattr(response, "content", None):
            raise RuntimeError(
                "Claude returned no response."
            )

        text = "".join(
            block.text
            for block in response.content
            if hasattr(block, "text")
        ).strip()

        if not text:
            raise RuntimeError(
                "Claude returned an empty response."
            )

        return text
