import unittest
from unittest.mock import patch

from providers.base import (
    _default_is_transient,
    classify_provider_error,
    retry_transient,
)


class ProviderErrorClassificationTests(
    unittest.TestCase
):

    def test_daily_gemini_quota_is_not_immediately_retried(
        self,
    ):
        exc = RuntimeError(
            "429 RESOURCE_EXHAUSTED: "
            "quota exceeded for "
            "GenerateRequestsPerDayPerProjectPerModel-FreeTier "
            "generate_content_free_tier_requests"
        )

        report = (
            classify_provider_error(
                exc
            )
        )

        self.assertTrue(
            report[
                "provider_related"
            ]
        )

        self.assertEqual(
            report["kind"],
            "quota_exhausted",
        )

        self.assertEqual(
            report["stage"],
            "provider-quota-exhausted",
        )

        self.assertFalse(
            report[
                "retry_inside_call"
            ]
        )

        self.assertFalse(
            _default_is_transient(
                exc
            )
        )

    def test_generic_429_remains_bounded_transient(
        self,
    ):
        exc = RuntimeError(
            "429 Too Many Requests"
        )

        report = (
            classify_provider_error(
                exc
            )
        )

        self.assertEqual(
            report["kind"],
            "rate_limited",
        )

        self.assertEqual(
            report["stage"],
            "provider-rate-limited",
        )

        self.assertTrue(
            report[
                "retry_inside_call"
            ]
        )

    def test_503_remains_transient(
        self,
    ):
        exc = RuntimeError(
            "503 UNAVAILABLE: "
            "provider overloaded"
        )

        report = (
            classify_provider_error(
                exc
            )
        )

        self.assertEqual(
            report["kind"],
            "temporarily_unavailable",
        )

        self.assertTrue(
            report[
                "retry_inside_call"
            ]
        )

    def test_auth_failure_is_not_retried(
        self,
    ):
        exc = RuntimeError(
            "401 unauthorized: "
            "API key not valid"
        )

        report = (
            classify_provider_error(
                exc
            )
        )

        self.assertEqual(
            report["kind"],
            "authentication",
        )

        self.assertEqual(
            report["stage"],
            "provider-auth-failed",
        )

        self.assertFalse(
            report[
                "retry_inside_call"
            ]
        )

    def test_unknown_failure_is_not_assumed_transient(
        self,
    ):
        exc = RuntimeError(
            "malformed response"
        )

        report = (
            classify_provider_error(
                exc
            )
        )

        self.assertFalse(
            report[
                "provider_related"
            ]
        )

        self.assertFalse(
            report[
                "retry_inside_call"
            ]
        )

    @patch(
        "providers.base.time.sleep"
    )
    def test_daily_quota_is_called_only_once(
        self,
        mocked_sleep,
    ):
        calls = {
            "count": 0
        }

        def fail():
            calls["count"] += 1

            raise RuntimeError(
                "429 RESOURCE_EXHAUSTED "
                "quota exceeded "
                "GenerateRequestsPerDayPerProjectPerModel-FreeTier "
                "free_tier_requests"
            )

        with self.assertRaises(
            RuntimeError
        ):
            retry_transient(
                fail,
                attempts=3,
                base_delay=0,
            )

        self.assertEqual(
            calls["count"],
            1,
        )

        mocked_sleep.assert_not_called()

    @patch(
        "providers.base.time.sleep"
    )
    def test_503_can_still_retry_and_succeed(
        self,
        mocked_sleep,
    ):
        calls = {
            "count": 0
        }

        def flaky():
            calls["count"] += 1

            if calls["count"] < 3:
                raise RuntimeError(
                    "503 UNAVAILABLE"
                )

            return "ok"

        result = retry_transient(
            flaky,
            attempts=3,
            base_delay=0,
        )

        self.assertEqual(
            result,
            "ok",
        )

        self.assertEqual(
            calls["count"],
            3,
        )

        self.assertEqual(
            mocked_sleep.call_count,
            2,
        )


if __name__ == "__main__":
    unittest.main()
