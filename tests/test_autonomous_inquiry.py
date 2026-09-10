import tempfile
import unittest

from brain.autonomous_inquiry import AutonomousInquiryCycle
from brain.curiosity import CuriosityEngine
from brain.evaluator import OutputEvaluator
from brain.memory import MemoryEngine


class Provider:
    def generate(self, prompt):
        return "QUESTION: How do people preserve knowledge when technology disappears?\nCRITERIA: Compare at least two traceable historical or academic sources."


class AutonomousInquiryTests(unittest.TestCase):
    def test_originates_a_fresh_question_after_all_current_questions_are_exhausted(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("lessons", "AION learned to preserve evidence.", "lesson")
            curiosity = CuriosityEngine(memory)
            old = curiosity.raise_question("Old question", "Find one source", budget=1)
            curiosity.record_attempt(old["id"], "Tried one source")
            report = AutonomousInquiryCycle(memory, Provider(), OutputEvaluator()).run_once()
            self.assertEqual("originated", report["stage"])
            self.assertTrue(report["originated"])
            self.assertEqual(2, len(curiosity.open_questions()))
            self.assertEqual(1, len(memory.all("autonomous_inquiries")))

    def test_keeps_out_of_the_way_when_normal_learning_is_still_possible(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            CuriosityEngine(memory).raise_question("Live question", "Find one source")
            report = AutonomousInquiryCycle(memory, Provider(), OutputEvaluator()).run_once()
            self.assertEqual("learning-already-active", report["stage"])
            self.assertFalse(report["originated"])

