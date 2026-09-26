import json
import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.research_story_handoff import ResearchStoryHandoff


class ResearchStoryHandoffTests(unittest.TestCase):
    def test_creates_a_bounded_batch_of_handoffs_instead_of_stopping_at_one(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            for index in range(2):
                memory.remember("story_research_briefs", json.dumps({
                    "status": "research-ready", "root_question_id": f"q{index}", "memory_id": f"brief{index}",
                    "topic": f"Why does ice last in a desert, case {index}?", "source_count": 2,
                    "sources": [{"evidence_memory_id": f"e{index}a"}, {"evidence_memory_id": f"e{index}b"}],
                    "unknown_facts": "The exact early timeline remains uncertain.",
                    "cognitive_uncertainties": "Do not infer more than sources show.",
                }), "decision")
            handoff = ResearchStoryHandoff(memory)
            result = handoff.create_batch(limit=5)
            self.assertEqual("story-handoff-batch-complete", result["stage"])
            self.assertEqual(2, result["created_count"])
            self.assertEqual("waiting-for-research-brief", handoff.create_batch(limit=5)["stage"])

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
            # Owner, 2026-09-27: lead the public title with the hook itself,
            # not a repeated "AION Wonders:" channel-name prefix -- matches
            # every one of the 4 comparable channels studied that day.
            self.assertEqual("Why does ice last in a desert?", result["handoff"]["working_title"])
            self.assertTrue(result["handoff"]["work_task_id"])
            self.assertEqual("waiting-for-research-brief", ResearchStoryHandoff(memory).create_once()["stage"])
