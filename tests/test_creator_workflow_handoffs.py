import unittest
from pathlib import Path


class CreatorWorkflowHandoffTests(unittest.TestCase):
    def test_motion_completion_triggers_assembly(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "assemble-creator-episode.yml")
        self.assertIn("AION - automatic motion production", workflow.read_text(encoding="utf-8"))

    def test_motion_and_assembly_workers_drain_a_bounded_ready_batch(self):
        root = Path(__file__).resolve().parents[1]
        motion = (root / ".github" / "workflows" / "creator-motion-production.yml").read_text(encoding="utf-8")
        assembly = (root / ".github" / "workflows" / "assemble-creator-episode.yml").read_text(encoding="utf-8")
        self.assertIn("produce_creator_motion.py --limit 5 --require-complete", motion)
        self.assertIn("assemble_creator_episode.py --limit 5 --require-rendered", assembly)
