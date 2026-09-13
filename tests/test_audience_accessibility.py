import json
import tempfile
import unittest

from brain.audience_accessibility import AudienceAccessibility, AudienceAccessibilityGate
from brain.memory import MemoryEngine


class AudienceAccessibilityTests(unittest.TestCase):
    def test_does_not_invent_retention_when_no_platform_metric_exists(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("social_feedback", json.dumps({"comments": 3}), "observation")
            report = AudienceAccessibility(memory).snapshot()
            self.assertEqual(0, report["retention_records"])
            self.assertIn("ยังไม่มี", report["retention_state"])

    def test_gate_makes_missing_accessibility_metadata_visible(self):
        report = AudienceAccessibilityGate().assess({"viewer_value": "A clear takeaway"})
        self.assertTrue(report["eligible"])
        self.assertIn("uncertainty-boundary-not-stated", report["review"])
