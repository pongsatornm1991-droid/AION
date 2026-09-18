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


if __name__ == "__main__":
    unittest.main()
