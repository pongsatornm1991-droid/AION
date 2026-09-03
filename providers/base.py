import time
from abc import ABC, abstractmethod


class AIProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


def _default_is_transient(exc):
    """True for errors that look like a temporary provider hiccup rather
    than a real problem: an overloaded/rate-limited AI provider or a
    dropped connection. Matched on the stringified error rather than
    provider-specific exception types, since each provider (Gemini,
    Claude, an OpenAI-compatible endpoint) raises its own SDK's error
    classes and this helper is shared across all of them."""

    text = str(exc).lower()
    markers = (
        "503", "unavailable", "overloaded", "429", "rate limit",
        "rate_limit", "timeout", "timed out", "connection",
        "temporarily", "try again",
    )
    return any(marker in text for marker in markers)


def retry_transient(call, attempts=3, base_delay=2.0, is_transient=None):
    """Call `call()` (a zero-argument callable) up to `attempts` times,
    retrying only errors that look transient, with a short exponential
    backoff between tries. Anything else -- a bad prompt, an auth
    failure, a malformed response -- is raised immediately on the first
    attempt, so a real problem is never silently retried and hidden
    behind a delay.

    AION's drafting cycles (SocialContentGenerator.draft_post() and
    friends) run once per scheduled GitHub Actions job with no retry of
    their own -- a single transient blip used to cost that entire
    cycle's post outright. Gemini's "503 UNAVAILABLE / high demand,
    please try again later" is the failure actually observed in
    production; this exists to absorb exactly that class of error
    without masking a genuine failure (bad API key, empty prompt, and
    so on), which still raises on the first try as before.
    """

    is_transient = is_transient or _default_is_transient

    last_exc = None
    for attempt in range(attempts):
        try:
            return call()
        except Exception as exc:
            if not is_transient(exc) or attempt == attempts - 1:
                raise
            last_exc = exc
            time.sleep(base_delay * (2 ** attempt))
    raise last_exc  # pragma: no cover -- loop above always returns or raises