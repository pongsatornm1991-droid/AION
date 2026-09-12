import unittest
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
