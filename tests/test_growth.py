"""Offline tests for audience-evidence growth insights."""

import json
import tempfile
import unittest

from brain.growth import GrowthEngine
from brain.memory import MemoryEngine


class GrowthEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.memory = MemoryEngine(root=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _media(self, media_id, likes, comments, caption):
        self.memory.remember(
            category="social_feedback",
            content=json.dumps({"kind": "media", "media_id": media_id, "like_count": likes,
                                "comments_count": comments, "caption": caption}),
            memory_type="observation", source="instagram-feedback", importance=2,
        )

    def test_waits_for_enough_distinct_posts(self):
        self._media("one", 3, 0, "one")
        self.assertEqual(GrowthEngine(self.memory).reflect_once()["stage"], "insufficient-data")

    def test_records_the_best_observed_theme_once(self):
        self._media("one", 3, 0, "memory")
        self._media("two", 1, 4, "connection")
        self._media("three", 4, 0, "dream")
        engine = GrowthEngine(self.memory)
        report = engine.reflect_once()
        self.assertEqual(report["stage"], "learned")
        self.assertIn("connection", report["guidance"])
        self.assertEqual(engine.reflect_once()["stage"], "unchanged")
