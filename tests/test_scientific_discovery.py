import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.scientific_discovery import ScientificDiscoveryLab


class ScientificDiscoveryTests(unittest.TestCase):
    def test_protocol_is_bounded_and_traceable(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = memory.remember("questions", "Question: Can passive cooling reduce heat?", "question")
            result = ScientificDiscoveryLab(memory).propose_once()
            self.assertEqual("protocol-created", result["stage"])
            self.assertEqual(question["id"], result["protocol"]["question_id"])
            self.assertIn("No human", result["protocol"]["boundary"])

    def test_does_not_duplicate_a_queued_question(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("questions", "A question", "question")
            lab = ScientificDiscoveryLab(memory)
            lab.propose_once()
            self.assertEqual("no-unassigned-question", lab.propose_once()["stage"])
