import tempfile
import unittest

from brain.initiative import AutonomousInitiative
from brain.curiosity import CuriosityEngine
from brain.memory import MemoryEngine


class AutonomousInitiativeTests(unittest.TestCase):
    def test_seeds_an_evidence_bound_question_when_idle(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            report = AutonomousInitiative(memory).initiate_once()
            self.assertEqual("seeded-question", report["stage"])
            question = CuriosityEngine(memory).open_questions()[0]
            self.assertIn("two independent credible sources", question["criteria"])
            self.assertEqual(1, len(memory.all("autonomous_initiatives")))

    def test_never_adds_a_second_question_to_an_active_queue(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            CuriosityEngine(memory).raise_question("Existing inquiry", "Cite a source.")
            self.assertEqual("question-already-open", AutonomousInitiative(memory).initiate_once()["stage"])
            self.assertEqual(1, len(CuriosityEngine(memory).open_questions()))
