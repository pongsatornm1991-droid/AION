import time
from abc import ABC, abstractmethod


class AIProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


def classify_provider_error(exc):
    """
    Classify provider failures without depending on one SDK's
    exception classes.

    The project supports multiple providers, so classification is
    deliberately based on stable error-message signals.

    Important distinction:

    - Daily/project quota exhaustion:
        NOT useful to retry immediately inside one provider call.

    - Short rate limit / overload / timeout / dropped connection:
        may be worth a small bounded retry.

    - Authentication/configuration failures:
        never retry automatically.

    - Unknown errors:
        are not assumed to be transient.
    """

    text = str(exc or "").lower()

    # --------------------------------------------------------
    # DAILY / PROJECT QUOTA EXHAUSTION
    # --------------------------------------------------------

    daily_quota_markers = (
        "requestsperday",
        "requests per day",
        "perday",
        "per day",
        "daily quota",
        "free_tier_requests",
        "free tier requests",
        "generate_content_free_tier_requests",
        "generate requests per day",
        "perprojectpermodel-freetier",
    )

    quota_language = (
        "quota exceeded",
        "resource_exhausted",
        "resource exhausted",
    )

    daily_quota = (
        any(
            marker in text
            for marker in daily_quota_markers
        )
        and any(
            marker in text
            for marker in quota_language
        )
    )

    if daily_quota:
        return {
            "provider_related": True,
            "kind": "quota_exhausted",
            "stage": "provider-quota-exhausted",
            "retriable_later": True,
            "retry_inside_call": False,
        }

    # --------------------------------------------------------
    # AUTH / CONFIGURATION
    # --------------------------------------------------------

    auth_markers = (
        "401",
        "403",
        "unauthorized",
        "permission denied",
        "permission_denied",
        "invalid api key",
        "api key not valid",
        "api_key_invalid",
        "authentication",
        "credentials",
    )

    if any(
        marker in text
        for marker in auth_markers
    ):
        return {
            "provider_related": True,
            "kind": "authentication",
            "stage": "provider-auth-failed",
            "retriable_later": False,
            "retry_inside_call": False,
        }

    # --------------------------------------------------------
    # TEMPORARY RATE LIMIT
    # --------------------------------------------------------

    rate_limit_markers = (
        "429",
        "rate limit",
        "rate_limit",
        "too many requests",
    )

    if any(
        marker in text
        for marker in rate_limit_markers
    ):
        return {
            "provider_related": True,
            "kind": "rate_limited",
            "stage": "provider-rate-limited",
            "retriable_later": True,
            "retry_inside_call": True,
        }

    # --------------------------------------------------------
    # TEMPORARY PROVIDER / NETWORK FAILURE
    # --------------------------------------------------------

    temporary_markers = (
        "503",
        "unavailable",
        "overloaded",
        "timeout",
        "timed out",
        "connection",
        "temporarily",
        "try again",
        "high demand",
    )

    if any(
        marker in text
        for marker in temporary_markers
    ):
        return {
            "provider_related": True,
            "kind": "temporarily_unavailable",
            "stage": "provider-temporarily-unavailable",
            "retriable_later": True,
            "retry_inside_call": True,
        }

    # --------------------------------------------------------
    # UNKNOWN / NON-PROVIDER-SPECIFIC ERROR
    # --------------------------------------------------------

    return {
        "provider_related": False,
        "kind": "unknown",
        "stage": None,
        "retriable_later": False,
        "retry_inside_call": False,
    }


def _default_is_transient(exc):
    """
    True only when retrying immediately inside the current provider
    request may reasonably succeed.

    Daily/project quota exhaustion deliberately returns False.
    """

    report = classify_provider_error(
        exc
    )

    return bool(
        report.get(
            "retry_inside_call"
        )
    )


def retry_transient(
    call,
    attempts=3,
    base_delay=2.0,
    is_transient=None,
):
    """
    Call call() with a small bounded retry only for failures that may
    recover immediately.

    Daily/project quota exhaustion is intentionally not retried here.
    It is raised immediately so the calling cycle can stop safely and
    remain retriable later.
    """

    is_transient = (
        is_transient
        or _default_is_transient
    )

    last_exc = None

    for attempt in range(
        attempts
    ):
        try:
            return call()

        except Exception as exc:
            if (
                not is_transient(exc)
                or attempt
                == attempts - 1
            ):
                raise

            last_exc = exc

            time.sleep(
                base_delay
                * (2 ** attempt)
            )

    raise last_exc
