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

    def test_creates_a_grounded_brief_once_and_keeps_uncertainty_visible(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How do coral reefs recover?", "Compare two cited sources.", priority=4,
            )
            self._evidence(memory, question, "Source one", "https://example.org/one", "Observation one.")
            self._evidence(memory, question, "Source two", "https://example.org/two", "Observation two.")
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
