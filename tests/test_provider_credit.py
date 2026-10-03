import tempfile
import unittest
from unittest import mock

from brain.memory import MemoryEngine
from brain.provider_credit import probe_openai_credit
from brain.system_integrity import SystemIntegrity


class _Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class ProbeTests(unittest.TestCase):
    def test_an_accepted_request_means_credit_is_fine(self):
        result = probe_openai_credit("k", post=lambda key, payload: _Response(200))
        self.assertEqual("ok", result["state"])

    def test_an_exhausted_balance_is_named_with_its_status_and_code(self):
        # The exact failure of 2026-10-03: HTTP 429 credit_balance_exhausted.
        post = lambda key, payload: _Response(429, {"error": {"code": "credit_balance_exhausted", "message": "secret"}})
        result = probe_openai_credit("k", post=post)
        self.assertEqual("exhausted", result["state"])
        self.assertEqual("HTTP 429 credit_balance_exhausted", result["detail"])
        self.assertNotIn("secret", str(result))

    def test_other_errors_are_unknown_never_exhausted(self):
        for response in (_Response(401, {"error": {"code": "invalid_api_key"}}), _Response(500), _Response(429, {"error": {"code": "rate_limit_exceeded"}})):
            self.assertEqual("unknown", probe_openai_credit("k", post=lambda key, payload, r=response: r)["state"])

    def test_a_network_error_or_missing_key_never_raises(self):
        def boom(key, payload):
            raise ConnectionError("offline")

        self.assertEqual("unknown", probe_openai_credit("k", post=boom)["state"])
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual("unknown", probe_openai_credit()["state"])

    def test_the_probe_asks_for_one_character_only(self):
        seen = {}
        probe_openai_credit("k", post=lambda key, payload: seen.update(payload) or _Response(200))
        self.assertEqual(".", seen["input"])


class IntegrityAlertTests(unittest.TestCase):
    def snapshot(self, probe):
        with tempfile.TemporaryDirectory() as root:
            return SystemIntegrity(MemoryEngine(root), root, credit_probe=probe).snapshot()

    def test_exhausted_credit_raises_a_critical_alert(self):
        report = self.snapshot(lambda: {"state": "exhausted", "detail": "HTTP 429 credit_balance_exhausted"})
        alert = next(a for a in report["alerts"] if a["check"] == "provider-credit-exhausted")
        self.assertEqual("critical", alert["severity"])
        self.assertEqual("critical", report["state"])
        self.assertIn("credit_balance_exhausted", alert["detail"])

    def test_healthy_unknown_or_missing_probe_raises_nothing(self):
        for probe in (lambda: {"state": "ok"}, lambda: {"state": "unknown", "detail": "x"}, None):
            report = self.snapshot(probe)
            self.assertFalse([a for a in report["alerts"] if a["check"] == "provider-credit-exhausted"])

    def test_a_crashing_probe_is_contained(self):
        def boom():
            raise RuntimeError("x")

        report = self.snapshot(boom)
        self.assertEqual("unknown", report["checks"]["provider_credit"]["state"])


if __name__ == "__main__":
    unittest.main()
