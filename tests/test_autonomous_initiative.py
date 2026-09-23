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

    def test_recovery_lane_adds_a_short_friendly_question_without_erasing_other_work(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            curiosity = CuriosityEngine(memory)
            original = curiosity.raise_question(
                "Existing deep inquiry", "Cite two sources.", priority=3
            )

            report = AutonomousInitiative(memory, curiosity).initiate_recovery_once(7)

            self.assertEqual("seeded-recovery-question", report["stage"])
            self.assertTrue(report["created"])
            self.assertEqual(5, report["question"]["importance"])
            self.assertIn("shorts-recovery", report["question"]["tags"])
            recovery = next(
                entry for entry in curiosity.open_questions()
                if entry["id"] == report["question"]["id"]
            )
            self.assertIn("50–60 second factual Short", recovery["criteria"])
            self.assertIn(
                original["id"],
                {entry["id"] for entry in curiosity.open_questions()},
            )

    def test_recovery_lane_reuses_an_active_question_and_stays_quiet_when_healthy(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            planner = AutonomousInitiative(memory)
            created = planner.initiate_recovery_once(1)
            active = planner.initiate_recovery_once(7)

            self.assertEqual("recovery-question-active", active["stage"])
            self.assertFalse(active["created"])
            self.assertEqual(created["question"]["id"], active["question"]["id"])
            self.assertEqual("buffer-healthy", planner.initiate_recovery_once(0)["stage"])
