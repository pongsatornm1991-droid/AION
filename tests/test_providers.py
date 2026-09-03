"""Offline tests for providers/base.py's retry_transient() helper.

No network access, no AI provider: pure-function tests only. time.sleep
is patched to a no-op so the retry-then-succeed and exhausted-retries
cases run instantly instead of actually waiting out the backoff.
"""

import unittest
from unittest.mock import patch

from providers.base import retry_transient


class RetryTransientTests(unittest.TestCase):

    @patch("providers.base.time.sleep", lambda _seconds: None)
    def test_retries_transient_error_then_succeeds(self):
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] < 3:
                raise RuntimeError("503 UNAVAILABLE: model overloaded, try again later")
            return "ok"

        self.assertEqual(retry_transient(flaky), "ok")
        self.assertEqual(calls["count"], 3)

    @patch("providers.base.time.sleep", lambda _seconds: None)
    def test_does_not_retry_non_transient_error(self):
        calls = {"count": 0}

        def bad_prompt():
            calls["count"] += 1
            raise ValueError("Prompt cannot be empty.")

        with self.assertRaises(ValueError):
            retry_transient(bad_prompt)
        self.assertEqual(calls["count"], 1)

    @patch("providers.base.time.sleep", lambda _seconds: None)
    def test_raises_after_exhausting_attempts_on_persistent_transient_error(self):
        calls = {"count": 0}

        def always_overloaded():
            calls["count"] += 1
            raise RuntimeError("429 rate limit exceeded")

        with self.assertRaises(RuntimeError):
            retry_transient(always_overloaded, attempts=3)
        self.assertEqual(calls["count"], 3)


if __name__ == "__main__":
    unittest.main()
