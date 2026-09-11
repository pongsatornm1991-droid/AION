import json
import tempfile
import unittest
from pathlib import Path

from brain.community_campaign import CommunityCampaignRegistry


class CommunityCampaignRegistryTests(unittest.TestCase):
    def test_snapshot_keeps_pending_admin_separate_from_ready_work(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "campaigns.json"
            path.write_text(json.dumps({"campaigns": [
                {"id": "sent", "status": "submitted-pending-admin"},
                {"id": "next", "status": "ready"},
            ]}), encoding="utf-8")
            snapshot = CommunityCampaignRegistry(path).snapshot()

            self.assertEqual("sent", snapshot["current"]["id"])
            self.assertEqual(1, snapshot["waiting_admin_count"])
            self.assertEqual(1, snapshot["ready_count"])
            self.assertIn("รอผู้ดูแล", snapshot["next"])

    def test_invalid_records_never_crash_the_dashboard_reader(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "campaigns.json"
            path.write_text(json.dumps({"campaigns": [None, {"id": "ok", "status": "unknown"}, {"id": "ok"}]}), encoding="utf-8")
            campaigns = CommunityCampaignRegistry(path).campaigns()

            self.assertEqual(1, len(campaigns))
            self.assertEqual("paused", campaigns[0]["status"])

    def test_transition_records_observed_status_without_skipping_the_queue(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "campaigns.json"
            path.write_text(json.dumps({"campaigns": [{"id": "one", "status": "ready"}]}), encoding="utf-8")
            registry = CommunityCampaignRegistry(path)

            updated = registry.transition("one", "submitted-pending-admin", "sent through the group composer")

            self.assertEqual("updated", updated["stage"])
            self.assertEqual("submitted-pending-admin", updated["campaign"]["status"])
            self.assertEqual("ready", updated["campaign"]["status_history"][0]["from"])
            with self.assertRaisesRegex(ValueError, "invalid campaign transition"):
                registry.transition("one", "published")
