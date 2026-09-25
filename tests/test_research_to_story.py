import json
import tempfile
import unittest

from brain.curiosity import CuriosityEngine
from brain.learning import ResearchEvidenceStore
from brain.memory import MemoryEngine
from brain.research_to_story import ResearchToStory


class ResearchToStoryTests(unittest.TestCase):
    def _evidence(self, memory, question, title, url, observation):
        return ResearchEvidenceStore(memory, CuriosityEngine(memory)).remember(
            question["id"], question["id"], "official_primary", title, url, observation,
        )

    def test_requires_two_traceable_sources_before_creating_a_story_brief(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How do coral reefs recover?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, question, "Source one", "https://example.org/one", "Observation one.")
            result = ResearchToStory(memory).propose_once()
            self.assertEqual("waiting-for-qualified-research", result["stage"])

    def test_proposes_a_bounded_batch_of_briefs_instead_of_stopping_at_one(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            first = CuriosityEngine(memory).raise_question(
                "How do coral reefs recover?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, first, "Source one", "https://one.test/one", "Observation one.")
            self._evidence(memory, first, "Source two", "https://two.test/two", "Observation two.")
            second = CuriosityEngine(memory).raise_question(
                "Why do deserts get cold at night?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, second, "Source three", "https://three.test/one", "Observation three.")
            self._evidence(memory, second, "Source four", "https://four.test/two", "Observation four.")
            pipeline = ResearchToStory(memory)
            result = pipeline.propose_batch(limit=5)
            self.assertEqual("story-brief-batch-complete", result["stage"])
            self.assertEqual(2, result["created_count"])
            self.assertEqual("waiting-for-qualified-research", pipeline.propose_batch(limit=5)["stage"])

    def test_creates_a_grounded_brief_once_and_keeps_uncertainty_visible(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How do coral reefs recover?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, question, "Source one", "https://one.test/one", "Observation one.")
            self._evidence(memory, question, "Source two", "https://two.test/two", "Observation two.")
            pipeline = ResearchToStory(memory)
            result = pipeline.propose_once()
            brief = result["brief"]
            self.assertEqual("brief-created", result["stage"])
            self.assertEqual(2, brief["source_count"])
            self.assertIn("every visual beat", brief["creative_direction"]["aion_presence"])
            self.assertTrue(brief["unknown_facts"])
            self.assertTrue(brief["cognitive_uncertainties"])
            self.assertEqual("waiting-for-qualified-research", pipeline.propose_once()["stage"])
            snapshot = pipeline.snapshot()
            self.assertEqual("research-ready", snapshot["status"])
            self.assertEqual(question["id"], snapshot["current"]["root_question_id"])

    def test_a_curated_source_package_gets_a_non_production_expansion_map(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "Why did people begin using money instead of trading everything directly?",
                "Compare two cited sources.", priority=4,
                tags=["human-history-money"],
            )
            self._evidence(memory, question, "Source one", "https://one.test/money", "Observation one.")
            self._evidence(memory, question, "Source two", "https://two.test/money", "Observation two.")

            brief = ResearchToStory(memory).propose_once()["brief"]
            self.assertEqual("planned", brief["content_expansion"]["status"])
            self.assertEqual(2, len(brief["content_expansion"]["follow_up_angles"]))
            self.assertTrue(all(
                angle["status"] == "needs-independent-evidence"
                for angle in brief["content_expansion"]["follow_up_angles"]
            ))

    def test_company_wide_published_topic_cannot_return_to_story_production(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("published_reels", json.dumps({"topic_key": "How Yakhchal stored ice in desert summers"}),
                            memory_type="action", source="test")
            question = CuriosityEngine(memory).raise_question(
                "How did Yakhchal store ice in desert summers?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, question, "Source one", "https://one.test/one", "Observation one.")
            self._evidence(memory, question, "Source two", "https://two.test/two", "Observation two.")
            result = ResearchToStory(memory).propose_once()
            self.assertEqual("blocked-duplicate-topic", result["stage"])

    def test_prefers_an_underrepresented_research_lane_over_alphabetical_order(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            pipeline = ResearchToStory(memory)

            # First brief: the only candidate, lands in the space-and-scale lane.
            universe_q = CuriosityEngine(memory).raise_question(
                "What is beyond the edge of the observable universe?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, universe_q, "Source one", "https://one.test/universe-a", "Observation one.")
            self._evidence(memory, universe_q, "Source two", "https://two.test/universe-b", "Observation two.")
            first = pipeline.propose_once()
            self.assertEqual("brief-created", first["stage"])
            self.assertEqual("space-and-scale", first["brief"]["scout_lane"]["id"])

            # Two more candidates become eligible at once: one alphabetically
            # first but in the now-once-used space-and-scale lane, one
            # alphabetically second but in an untouched lane (nature-and-earth).
            galaxy_q = CuriosityEngine(memory).raise_question(
                "Are black holes hiding at the center of every galaxy?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, galaxy_q, "Source one", "https://one.test/galaxy-a", "Observation one.")
            self._evidence(memory, galaxy_q, "Source two", "https://two.test/galaxy-b", "Observation two.")
            coral_q = CuriosityEngine(memory).raise_question(
                "How do coral reefs recover?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, coral_q, "Source one", "https://one.test/coral-a", "Observation one.")
            self._evidence(memory, coral_q, "Source two", "https://two.test/coral-b", "Observation two.")

            # Alphabetically, the galaxy topic ("Are...") sorts before the
            # coral topic ("How..."), so the old alphabetical-only order would
            # pick it again -- concentrating a second brief into the lane
            # that already has one, exactly the imbalance found on the
            # Operations dashboard on 2026-09-26.
            second = pipeline.propose_once()
            self.assertEqual("brief-created", second["stage"])
            self.assertEqual("nature-and-earth", second["brief"]["scout_lane"]["id"])

    def test_does_not_turn_explicitly_off_topic_observations_into_a_story_brief(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How do honeybees communicate a food location?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, question, "Source one", "https://one.test/one", "No relevant observation about how honeybees communicate food locations.")
            self._evidence(memory, question, "Source two", "https://two.test/two", "This source does not describe how honeybees communicate a food location.")
            self.assertEqual("waiting-for-qualified-research", ResearchToStory(memory).propose_once()["stage"])
