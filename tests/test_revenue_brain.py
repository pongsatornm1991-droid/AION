import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.revenue_brain import RevenueBrain


class RevenueBrainTests(unittest.TestCase):
    def test_proposes_only_a_bounded_validation_step_once(self):
        with tempfile.TemporaryDirectory() as root:
            brain = RevenueBrain(MemoryEngine(root))
            first = brain.propose_once()
            self.assertEqual("proposed", first["stage"])
            self.assertIn("owner_required", first["proposal"])
            self.assertEqual("unchanged", brain.propose_once()["stage"])

    def test_snapshot_waits_for_real_audience_signals(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            snapshot = RevenueBrain(memory).snapshot()
            self.assertEqual("validate-audience-value", snapshot["stage"])
            self.assertEqual(0, snapshot["audience_signals"])
            self.assertIn("No spending", snapshot["guardrails"][0])
