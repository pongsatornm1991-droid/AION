import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from brain.delivery_watchdog import DeliveryWatchdog
from brain.memory import MemoryEngine
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class DeliveryWatchdogTests(unittest.TestCase):
    def test_marks_recent_facebook_delivery_as_verified(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root=root)
            registry = ToolRegistry()
            registry.register("post_to_facebook", lambda message: {"id": "hidden"}, ActionLevel.HIGH_RISK)
            lifecycle = ToolLifecycle(memory, registry=registry)
            action = lifecycle.propose("post_to_facebook", {"message": "hello"}, source="test")
            approved = lifecycle.approve(action["id"], "reviewer")
            lifecycle.execute(approved["id"])

            report = DeliveryWatchdog(memory, root=root).snapshot(now=datetime.now(timezone.utc))
            facebook = next(item for item in report["platforms"] if item["platform"] == "facebook")

            self.assertEqual("verified", facebook["state"])
            self.assertIsNotNone(facebook["last_confirmed_at"])

    def test_marks_missing_or_old_evidence_for_attention(self):
        with tempfile.TemporaryDirectory() as root:
            report = DeliveryWatchdog(MemoryEngine(root=root), root=root).snapshot(
                now=datetime.now(timezone.utc) + timedelta(hours=31)
            )
            self.assertEqual("attention", report["summary"])
            self.assertTrue(all(item["state"] == "attention" for item in report["platforms"]))
