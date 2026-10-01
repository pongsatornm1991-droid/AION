import json
import tempfile
import unittest

from brain.content_expansion import ContentExpansionPlanner
from brain.curiosity import CuriosityEngine
from brain.memory import MemoryEngine


class ContentExpansionPlannerTests(unittest.TestCase):
    def _brief(self, root="money-root"):
        return {
            "root_question_id": root,
            "story_package_id": root,
            "topic": "Why did people begin using money instead of trading everything directly?",
            "question_tags": ["shorts-recovery", "human-history-money"],
            "sources": [
                {"url": "https://one.test/money", "evidence_memory_id": "source-one"},
                {"url": "https://two.test/money", "evidence_memory_id": "source-two"},
            ],
        }

    def test_preserves_distinct_follow_up_angles_without_promoting_them(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            result = ContentExpansionPlanner(memory).create_for_brief(self._brief())

            self.assertEqual("expansion-map-created", result["stage"])
            follow_ups = result["map"]["follow_up_angles"]
            self.assertEqual(4, len(follow_ups))
            self.assertTrue(all(item["status"] == "needs-independent-evidence" for item in follow_ups))
            self.assertEqual(
                {"specific-follow-up", "mechanism", "everyday-test"},
                {item["angle_type"] for item in follow_ups},
            )
            summary = result["map"]["creator_series_summary"]
            self.assertEqual(5, summary["planned_episode_count"])
            self.assertIn("one concrete surprise", summary["storytelling_rule"])
            self.assertIn("context only", result["map"]["boundary"])
            self.assertEqual("expansion-map-exists", ContentExpansionPlanner(memory).create_for_brief(self._brief())["stage"])

    def test_seeds_only_bounded_follow_ups_with_independent_evidence_rule(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            planner = ContentExpansionPlanner(memory)
            planner.create_for_brief(self._brief())

            seeded = planner.seed_pending_questions()
            self.assertEqual("expansion-questions-seeded", seeded["stage"])
            self.assertEqual(2, len(seeded["created"]))
            questions = CuriosityEngine(memory).open_questions()
            self.assertEqual(2, len(questions))
            self.assertTrue(all("independent, traceable sources" in item["criteria"] for item in questions))
            second = planner.seed_pending_questions()
            self.assertEqual("expansion-questions-seeded", second["stage"])
            self.assertEqual(2, len(second["created"]))
            self.assertEqual("no-pending-expansion-questions", planner.seed_pending_questions()["stage"])

    def test_queue_full_does_not_throw_away_the_preserved_map(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            planner = ContentExpansionPlanner(memory)
            planner.create_for_brief(self._brief())
            curiosity = CuriosityEngine(memory)
            for index in range(10):
                curiosity.raise_question(f"Existing question {index}", "Use cited evidence.")

            result = planner.seed_pending_questions()
            self.assertEqual("expansion-queue-full-preserved", result["stage"])
            snapshot = planner.snapshot()
            self.assertEqual(1, snapshot["source_packages"])
            self.assertEqual(5, snapshot["planned_creator_episodes"])

    def test_generic_story_gets_creator_angles_even_without_a_handwritten_family(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            brief = self._brief(root="moon-root")
            brief["topic"] = "Why do astronauts appear to float while orbiting Earth?"
            brief["question_tags"] = ["shorts-recovery", "space-orbits"]

            result = ContentExpansionPlanner(memory).create_for_brief(brief)

            angles = result["map"]["follow_up_angles"]
            self.assertEqual(3, len(angles))
            self.assertEqual(
                {"mechanism", "everyday-test", "boundary"},
                {item["angle_type"] for item in angles},
            )
            self.assertTrue(all("orbiting Earth" in item["question"] for item in angles))
