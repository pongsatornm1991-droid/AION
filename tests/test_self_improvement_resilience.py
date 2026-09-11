import unittest
from unittest.mock import patch

import main


class SelfImprovementResilienceTests(unittest.TestCase):
    def test_provider_outage_is_reported_not_raised(self):
        args = type("Args", (), {"min_claim_safety": 5, "min_occurrences": 3})()
        with patch("main.build_provider", side_effect=RuntimeError("offline")), patch("main._notify_report"):
            report = main.run_self_improvement_cycle(args)
        self.assertEqual("provider-unavailable", report["stage"])
        self.assertEqual("RuntimeError", report["error_type"])
