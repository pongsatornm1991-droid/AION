import json
import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from brain.research_planner import AutonomousResearchPlanner
from brain.social_signals_source import SocialSignalsSource
from brain.source_registry import SourceRegistry


class SocialSignalsSourceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.memory = MemoryEngine(Path(self.root.name) / "memory")

    def tearDown(self):
        self.root.cleanup()

    def _remember(self, source, payload):
        self.memory.remember(
            "social_feedback", json.dumps(payload), memory_type="observation",
            source=source, importance=2,
        )

    def test_returns_latest_youtube_snapshot_with_a_traceable_url(self):
        self._remember("youtube-public-analytics", {
            "video_id": "old", "title": "Older", "view_count": 1, "like_count": 0,
        })
        self._remember("youtube-public-analytics", {
            "video_id": "abc123", "title": "Why lightning strikes", "view_count": 120,
            "like_count": 12, "comment_count": 3,
        })
        source = SocialSignalsSource(self.memory)
        results = source.search("abc123", limit=5)
        self.assertEqual(1, len(results))
        item = source.fetch(results[0]["title"])
        self.assertEqual("https://www.youtube.com/watch?v=abc123", item["url"])
        self.assertIn("views=120", item["extract"])
        self.assertIn("do not reveal retention", item["extract"])

    def test_keeps_only_the_latest_snapshot_for_each_video(self):
        self._remember("youtube-public-analytics", {
            "video_id": "abc123", "title": "Lightning", "view_count": 10, "like_count": 1,
        })
        self._remember("youtube-public-analytics", {
            "video_id": "abc123", "title": "Lightning", "view_count": 99, "like_count": 8,
        })
        source = SocialSignalsSource(self.memory)
        results = source.search("", limit=5)
        self.assertEqual(1, len(results))
        self.assertIn("views=99", source.fetch(results[0]["title"])["extract"])

    def test_planner_can_route_platform_metrics_to_enabled_adapter(self):
        plan = AutonomousResearchPlanner(SourceRegistry()).plan(
            {"evidence_types": ["platform_metrics"], "required_count": None},
            available_adapter_ids={"social_signals"},
            topic="How are AION views and likes changing?",
        )
        self.assertEqual("ready", plan["status"])
        self.assertEqual("social_signals", plan["source_id"])


if __name__ == "__main__":
    unittest.main()
