import unittest
import tempfile
from brain.cyber_guard import CyberGuard
from brain.evolution_lab import EvolutionLab
from brain.memory import MemoryEngine


class NewWorkspaceTests(unittest.TestCase):
    def test_cyber_guard_is_defensive_and_secrets_are_ignored(self):
        snapshot = CyberGuard().snapshot()
        self.assertIn("ไม่สแกนโจมตี", snapshot["checks"][-1]["detail"])
        self.assertEqual("healthy", snapshot["status"])

    def test_evolution_lab_has_a_hard_boundary(self):
        snapshot = EvolutionLab(MemoryEngine()).snapshot()
        self.assertIn("ห้ามสร้างหรือปล่อย AI อิสระใหม่", snapshot["boundary"])

    def test_evolution_lab_exposes_proposal_detail_and_auto_experiment_state(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            proposal = memory.remember(
                "self_improvement", "Improve the opening hook.",
                memory_type="observation", source="test", importance=3,
            )
            memory.remember(
                "improvement_reviews",
                '{"review_id":"r1","proposal_id":"%s","status":"approved-for-experiment"}' % proposal["id"],
                memory_type="decision", source="test", importance=4,
            )
            memory.remember(
                "content_experiment_plans",
                '{"review_id":"r1","proposal_id":"%s","status":"queued","sample_size":4,"method":"Compare openings","success_signal":"Four outcomes","stop_rule":"Stop on quality decline"}' % proposal["id"],
                memory_type="experiment", source="test", importance=4,
            )
            item = EvolutionLab(memory).snapshot()["proposal_items"][0]
            self.assertEqual("กำลังทดลองอัตโนมัติ", item["status_label"])
            self.assertIn("Improve the opening hook.", item["detail"])
            self.assertEqual("Compare openings", item["experiment"]["method"])
