import tempfile
import unittest
import json

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
            self.assertEqual(0, report["content_expansion"]["source_packages"])
            self.assertEqual("critical", report["state"])
            self.assertIn("not evidence", report["boundary"])

    def test_does_not_count_a_historical_handed_off_brief_as_new_story_inventory(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("story_research_briefs", json.dumps({
                "status": "research-ready", "root_question_id": "q-old",
            }), "decision")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "staged-for-studio", "root_question_id": "q-old",
            }), "decision")

            report = EvidenceReserve(memory).snapshot()

            self.assertEqual(0, report["counts"]["story_briefs"])
            self.assertEqual(1, report["counts"]["historical_story_briefs"])
            self.assertEqual(1, report["counts"]["handed_to_story"])
