import json
import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.research_story_handoff import ResearchStoryHandoff


class ResearchStoryHandoffTests(unittest.TestCase):
    def test_creates_one_traceable_story_handoff_from_brief(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("story_research_briefs", json.dumps({
                "status": "research-ready", "root_question_id": "q1", "memory_id": "brief1",
                "topic": "Why does ice last in a desert?", "source_count": 2,
                "sources": [{"evidence_memory_id": "e1"}, {"evidence_memory_id": "e2"}],
                "unknown_facts": "The exact early timeline remains uncertain.",
                "cognitive_uncertainties": "Do not infer more than sources show.",
            }), "decision")
            result = ResearchStoryHandoff(memory).create_once()
            self.assertEqual("story-handoff-created", result["stage"])
            self.assertEqual(5, len(result["handoff"]["beats"]))
            self.assertIn("AION", result["handoff"]["visual_rule"])
            self.assertEqual("handoff-already-created", ResearchStoryHandoff(memory).create_once()["stage"])
