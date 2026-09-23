"""Guard the durable handoff contract of the release-buffer workflow."""

import unittest
from pathlib import Path


class ReleaseReadinessWorkflowTests(unittest.TestCase):
    def test_recovery_persists_private_handoffs_before_finishing(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "release-readiness.yml").read_text(encoding="utf-8")
        self.assertIn("Persist recovery handoffs before the next workflow can read them", workflow)
        self.assertIn("working-directory: memory_data", workflow)
        self.assertIn("AION release-buffer recovery handoff", workflow)

    def test_recovery_wakes_learning_when_evidence_is_missing(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "release-readiness.yml").read_text(encoding="utf-8")
        self.assertIn("Start evidence recovery when the buffer has no eligible story", workflow)
        self.assertIn("learning-cycle.yml/dispatches", workflow)

    def test_production_control_keeps_running_through_snapshot_conflicts(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "production-control.yml").read_text(encoding="utf-8")
        self.assertIn("aion-production-control.json", workflow)
        self.assertIn("GIT_EDITOR=true git rebase --continue", workflow)


if __name__ == "__main__":
    unittest.main()
