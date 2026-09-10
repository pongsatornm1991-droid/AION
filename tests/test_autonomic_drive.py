import tempfile
import unittest

from brain.autonomic_drive import AutonomicDrive
from brain.curiosity import CuriosityEngine
from brain.memory import MemoryEngine


class AutonomicDriveTests(unittest.TestCase):
    def test_prioritizes_research_when_a_question_can_still_be_investigated(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question("What changes with light?", "Find a source")
            report = AutonomicDrive(memory).decide_once()
            self.assertEqual("decided", report["stage"])
            self.assertEqual("research", report["decision"]["mode"])
            self.assertEqual(question["id"], report["decision"]["related"])

    def test_renews_inquiry_instead_of_waiting_when_existing_questions_are_exhausted(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            curiosity = CuriosityEngine(memory)
            question = curiosity.raise_question("Old question", "Find a source", budget=1)
            curiosity.record_attempt(question["id"])
            report = AutonomicDrive(memory).decide_once()
            self.assertEqual("originate-inquiry", report["decision"]["mode"])

    def test_same_state_does_not_create_fake_repeated_thoughts(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            CuriosityEngine(memory).raise_question("Live question", "Find a source")
            AutonomicDrive(memory).decide_once()
            again = AutonomicDrive(memory).decide_once()
            self.assertEqual("unchanged", again["stage"])
