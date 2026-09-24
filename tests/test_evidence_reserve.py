import tempfile
import unittest

from brain.evidence_reserve import EvidenceReserve
from brain.initiative import AutonomousInitiative
from brain.memory import MemoryEngine


class EvidenceReserveTests(unittest.TestCase):
    def test_counts_research_questions_without_calling_them_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            AutonomousInitiative(memory).initiate_recovery_batch(7, seed_limit=5)

            report = EvidenceReserve(memory).snapshot()

            self.assertEqual(5, report["counts"]["questions"])
            self.assertEqual(0, report["counts"]["qualified_evidence"])
            self.assertEqual(21, report["targets"]["questions"])
            self.assertEqual(14, report["targets"]["qualified_evidence"])
            self.assertEqual("critical", report["state"])
            self.assertIn("not evidence", report["boundary"])
