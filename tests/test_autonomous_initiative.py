import tempfile
import unittest
from unittest.mock import patch

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

    def test_recovery_lane_does_not_reopen_a_previous_recovery_question(self):
        # Regression for 2026-09-25: excluding by whole catalogue domain
        # (rather than the specific question actually asked) meant a
        # finite, never-expiring domain list eventually ran out entirely --
        # the real reserve hit 0/33 domains remaining and could never seed
        # another recovery question again, no matter how empty the Shorts
        # buffer was. The fix excludes a specific question once it has
        # actually been asked (any status), not its whole domain, so the
        # same domain can still contribute a different question.
        catalogue = (
            ("insect-science", "How do honeybees tell their nestmates where food is?", "Show a bee's dance."),
            ("insect-science", "Why do fireflies glow in the dark?", "Show a chemical reaction lighting an insect."),
        )
        with tempfile.TemporaryDirectory() as root, patch.object(AutonomousInitiative, "RECOVERY_INQUIRIES", catalogue):
            memory = MemoryEngine(root)
            curiosity = CuriosityEngine(memory)
            entry = curiosity.raise_question(
                catalogue[0][1], "Cite two sources.", priority=5, budget=1,
                tags=["shorts-recovery", "shorts-first", "insect-science"],
            )
            curiosity.record_attempt(entry["id"])

            report = AutonomousInitiative(memory, curiosity).initiate_recovery_once(7)

            self.assertEqual("seeded-recovery-question", report["stage"])
            seeded = next(q for q in curiosity.open_questions() if q["id"] == report["question"]["id"])
            self.assertEqual(catalogue[1][1], seeded["statement"])
            self.assertEqual("insect-science", report["domain"])

    def test_recovery_lane_stops_once_every_catalogue_question_is_asked(self):
        catalogue = (
            ("insect-science", "How do honeybees tell their nestmates where food is?", "Show a bee's dance."),
        )
        with tempfile.TemporaryDirectory() as root, patch.object(AutonomousInitiative, "RECOVERY_INQUIRIES", catalogue):
            memory = MemoryEngine(root)
            curiosity = CuriosityEngine(memory)
            entry = curiosity.raise_question(
                catalogue[0][1], "Cite two sources.", priority=5, budget=1,
                tags=["shorts-recovery", "shorts-first", "insect-science"],
            )
            curiosity.record_attempt(entry["id"])

            report = AutonomousInitiative(memory, curiosity).initiate_recovery_once(7)

            self.assertEqual("recovery-reserve-exhausted", report["stage"])
            self.assertIsNone(report["question"])

    def test_recovery_reserve_seeds_a_bounded_distinct_batch(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)

            report = AutonomousInitiative(memory).initiate_recovery_batch(
                7, target=21, seed_limit=5
            )

            self.assertEqual("seeded-recovery-reserve", report["stage"])
            self.assertEqual(5, report["created_count"])
            self.assertEqual(5, len(report["questions"]))
            self.assertEqual(5, len(set(report["created_domains"])))
            self.assertEqual(21, report["target"])
            self.assertTrue(all(
                "shorts-recovery" in question["tags"]
                for question in report["questions"]
            ))
            self.assertTrue(all(
                "shorts-fast-lane" in question["tags"]
                for question in report["questions"]
            ))

    def test_full_global_queue_is_preserved_without_crashing_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            curiosity = CuriosityEngine(memory)
            for index in range(curiosity.max_open):
                curiosity.raise_question(f"Existing {index}", "Use cited evidence.")

            report = AutonomousInitiative(memory, curiosity).initiate_recovery_batch(7)
            self.assertEqual("recovery-reserve-queue-full", report["stage"])
            self.assertEqual(0, report["created_count"])
            self.assertEqual(0, report["queue_capacity"])
