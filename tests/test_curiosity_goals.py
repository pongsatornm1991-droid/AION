"""Offline, filesystem-level tests for CuriosityEngine and GoalEngine
(both built on BoundedItemTracker).

No AI provider is involved anywhere in either component — opening,
attempting, resolving, and abandoning items is pure code, so this
suite needs no stub/mock provider and runs fully deterministically.
"""

import shutil
import tempfile
import unittest

from brain.curiosity import CuriosityEngine
from brain.goals import GoalEngine
from brain.memory import MemoryEngine


class CuriosityEngineTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_curiosity_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.curiosity = CuriosityEngine(self.memory, max_open=2)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_raise_question_requires_criteria(self):
        with self.assertRaises(ValueError):
            self.curiosity.raise_question("Why?", completion_criteria="")

    def test_raise_question_requires_statement(self):
        with self.assertRaises(ValueError):
            self.curiosity.raise_question("   ", completion_criteria="c")

    def test_raise_question_rejects_bad_priority(self):
        with self.assertRaises(ValueError):
            self.curiosity.raise_question("Why?", completion_criteria="c", priority=6)

    def test_raise_question_rejects_bad_budget(self):
        with self.assertRaises(ValueError):
            self.curiosity.raise_question("Why?", completion_criteria="c", budget=0)

    def test_raise_question_saves_and_survives_disk_roundtrip(self):
        saved = self.curiosity.raise_question(
            "Why does staged rollout help?",
            completion_criteria="Find 2 confirming decisions.",
            priority=4,
            budget=3,
            tags=["rollout"],
        )

        self.assertEqual(saved["importance"], 4)
        self.assertEqual(saved["tags"], ["rollout"])

        open_qs = self.curiosity.open_questions()
        self.assertEqual(len(open_qs), 1)
        self.assertEqual(open_qs[0]["statement"], "Why does staged rollout help?")
        self.assertEqual(open_qs[0]["criteria"], "Find 2 confirming decisions.")
        self.assertEqual(open_qs[0]["attempts"], 0)
        self.assertEqual(open_qs[0]["budget"], 3)
        self.assertFalse(open_qs[0]["budget_exhausted"])

    def test_bounded_max_open_refuses_beyond_cap(self):
        self.curiosity.raise_question("Q1", completion_criteria="c1")
        self.curiosity.raise_question("Q2", completion_criteria="c2")

        with self.assertRaises(ValueError):
            self.curiosity.raise_question("Q3", completion_criteria="c3")

    def test_resolving_one_frees_a_slot(self):
        first = self.curiosity.raise_question("Q1", completion_criteria="c1")
        self.curiosity.raise_question("Q2", completion_criteria="c2")

        self.curiosity.answer_question(
            first["id"], answer="Answer.", evidence=["note"]
        )

        # Third can now open since resolving Q1 freed a slot.
        third = self.curiosity.raise_question("Q3", completion_criteria="c3")
        self.assertIsNotNone(third["id"])

    def test_record_attempt_increments_and_supersedes(self):
        saved = self.curiosity.raise_question(
            "Q1", completion_criteria="c1", budget=2
        )

        attempt = self.curiosity.record_attempt(
            saved["id"], note="First try."
        )

        self.assertNotEqual(attempt["id"], saved["id"])

        open_qs = self.curiosity.open_questions()
        self.assertEqual(len(open_qs), 1)
        self.assertEqual(open_qs[0]["id"], attempt["id"])
        self.assertEqual(open_qs[0]["attempts"], 1)
        self.assertIn("First try.", open_qs[0]["progress"])
        self.assertFalse(open_qs[0]["budget_exhausted"])

    def test_budget_exhausted_flag_surfaces_without_forcing_a_transition(self):
        saved = self.curiosity.raise_question(
            "Q1", completion_criteria="c1", budget=1
        )
        attempt = self.curiosity.record_attempt(saved["id"])

        open_qs = self.curiosity.open_questions()
        self.assertEqual(len(open_qs), 1)
        self.assertTrue(open_qs[0]["budget_exhausted"])
        self.assertEqual(open_qs[0]["id"], attempt["id"])  # still open

    def test_answer_question_requires_evidence(self):
        saved = self.curiosity.raise_question("Q1", completion_criteria="c1")

        with self.assertRaises(ValueError):
            self.curiosity.answer_question(
                saved["id"], answer="Some answer.", evidence=[]
            )

    def test_answer_question_resolves_and_links_evidence(self):
        saved = self.curiosity.raise_question("Q1", completion_criteria="c1")

        answered = self.curiosity.answer_question(
            saved["id"],
            answer="Final answer.",
            evidence=[{"id": "dec1", "description": "Confirmed."}],
        )

        self.assertIn("dec1", answered["related"])
        self.assertEqual(self.curiosity.open_questions(), [])

    def test_cannot_attempt_or_answer_a_resolved_question(self):
        saved = self.curiosity.raise_question("Q1", completion_criteria="c1")
        answered = self.curiosity.answer_question(
            saved["id"], answer="Done.", evidence=["note"]
        )

        with self.assertRaises(ValueError):
            self.curiosity.record_attempt(answered["id"])

        with self.assertRaises(ValueError):
            self.curiosity.answer_question(
                answered["id"], answer="Again.", evidence=["note"]
            )

    def test_abandon_question_tags_and_logs_a_lesson(self):
        saved = self.curiosity.raise_question("Q1", completion_criteria="c1")
        self.curiosity.abandon_question(saved["id"], reason="No longer relevant.")

        self.assertEqual(self.curiosity.open_questions(), [])

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("Abandoned question", lessons[0]["content"])
        self.assertIn(saved["id"], lessons[0]["related"])

    def test_abandon_requires_reason(self):
        saved = self.curiosity.raise_question("Q1", completion_criteria="c1")

        with self.assertRaises(ValueError):
            self.curiosity.abandon_question(saved["id"], reason="   ")

    def test_history_walks_full_chain_across_attempts_and_resolution(self):
        first = self.curiosity.raise_question("Q1", completion_criteria="c1", budget=5)
        second = self.curiosity.record_attempt(first["id"], note="try 1")
        third = self.curiosity.record_attempt(second["id"], note="try 2")
        answered = self.curiosity.answer_question(
            third["id"], answer="Done.", evidence=["note"]
        )

        history = self.curiosity.history(answered["id"])

        self.assertEqual(
            [entry["id"] for entry in history],
            [first["id"], second["id"], third["id"], answered["id"]],
        )

    def test_topic_filter(self):
        self.curiosity.raise_question(
            "About rollout.", completion_criteria="c", tags=["rollout"]
        )
        self.curiosity.raise_question(
            "About something else.", completion_criteria="c", tags=["other"]
        )

        rollout_only = self.curiosity.open_questions(topic="rollout")
        self.assertEqual(len(rollout_only), 1)
        self.assertEqual(rollout_only[0]["statement"], "About rollout.")


class GoalEngineTests(unittest.TestCase):
    """Lighter coverage for GoalEngine: confirms the subclass wiring
    (labels, category, methods) is correct — the shared mechanics are
    already thoroughly covered by CuriosityEngineTests above."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_goals_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.goals = GoalEngine(self.memory, max_open=1)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_set_goal_requires_criteria(self):
        with self.assertRaises(ValueError):
            self.goals.set_goal("Ship it.", completion_criteria="")

    def test_full_lifecycle(self):
        saved = self.goals.set_goal(
            "Ship staged rollout tooling.",
            completion_criteria="Tool deployed and used once.",
            priority=5,
            budget=2,
        )

        self.assertEqual(saved["type"], "goal")

        with self.assertRaises(ValueError):
            self.goals.set_goal("Second goal.", completion_criteria="c")

        attempted = self.goals.record_attempt(saved["id"], note="Built prototype.")
        active = self.goals.active_goals()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["id"], attempted["id"])
        self.assertEqual(active[0]["attempts"], 1)

        completed = self.goals.complete_goal(
            attempted["id"],
            outcome="Deployed and used in production.",
            evidence=["deployment log"],
        )

        self.assertEqual(self.goals.active_goals(), [])

        history = self.goals.history(completed["id"])
        self.assertEqual(
            [entry["id"] for entry in history],
            [saved["id"], attempted["id"], completed["id"]],
        )

    def test_abandon_goal_logs_a_lesson(self):
        saved = self.goals.set_goal("Ship it.", completion_criteria="c")
        self.goals.abandon_goal(saved["id"], reason="Deprioritized.")

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("Abandoned goal", lessons[0]["content"])


if __name__ == "__main__":
    unittest.main()
