import unittest
from pathlib import Path


class CreatorWorkflowHandoffTests(unittest.TestCase):
    def test_motion_completion_triggers_assembly(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "assemble-creator-episode.yml")
        self.assertIn("AION - automatic motion production", workflow.read_text(encoding="utf-8"))
