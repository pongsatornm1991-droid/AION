import json
import tempfile
import unittest

from brain.curiosity import CuriosityEngine
from brain.memory import MemoryEngine
from brain.youtube_learning import YouTubeLearningCycle


class YouTubeLearningTests(unittest.TestCase):
    def test_records_discovery_but_never_resolves_the_question(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How do humans learn language?", "Find corroborated sources.", priority=4,
            )
            cycle = YouTubeLearningCycle(memory, search_fn=lambda query: [{
                "video_id": "abc", "url": "https://www.youtube.com/watch?v=abc",
                "title": "Language learning", "channel": "Trusted-looking channel", "description": "A lead only.",
            }])
            report = cycle.discover_once()
            self.assertEqual("discovered", report["stage"])
            self.assertEqual(question["id"], report["question"]["id"])
            self.assertEqual(1, len(CuriosityEngine(memory).open_questions()))
            record = json.loads(memory.all("youtube_discoveries")[0]["content"])
            self.assertIn("not evidence", record["epistemic_status"])
            self.assertEqual("already-discovered", cycle.discover_once()["stage"])

    def test_missing_key_is_an_honest_configuration_state(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            CuriosityEngine(memory).raise_question("What is memory?", "Find sources.")
            report = YouTubeLearningCycle(memory, search_fn=lambda query: (_ for _ in ()).throw(RuntimeError("YOUTUBE_DATA_API_KEY is required"))).discover_once()
            self.assertEqual("configuration-needed", report["stage"])

    def test_disabled_registry_makes_no_network_call(self):
        with tempfile.TemporaryDirectory() as root:
            class DisabledRegistry:
                def source(self, source_id):
                    return {"id": source_id, "enabled": False}
            cycle = YouTubeLearningCycle(MemoryEngine(root), search_fn=lambda query: self.fail("should not search"), source_registry=DisabledRegistry())
            self.assertEqual("source-disabled", cycle.discover_once()["stage"])
