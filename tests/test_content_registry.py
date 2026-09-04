import json
import tempfile
import unittest
from pathlib import Path

from brain.content_registry import CreatorContentRegistry
from brain.memory import MemoryEngine


class CreatorContentRegistryTests(unittest.TestCase):
    def _registry(self, root, seconds=7):
        root = Path(root); video = root / "content/reels/one.mp4"
        video.parent.mkdir(parents=True); video.write_bytes(b"x" * 100_001)
        path = root / "content/creator_library.json"
        path.write_text(json.dumps({"policy":{"scene_min_seconds":5,"scene_max_seconds":10},"episodes":[{
            "id":"one","title":"One","video_path":"content/reels/one.mp4","cover_path":"cover.png",
            "duration_seconds":seconds * 5,"scene_count":5,"caption":"A useful thought.","source_url":None
        }]}), encoding="utf-8")
        return CreatorContentRegistry(MemoryEngine(root / "memory"), path=path, root=root)

    def test_next_ready_becomes_queued_then_published(self):
        with tempfile.TemporaryDirectory() as root:
            registry = self._registry(root); self.assertEqual("one", registry.next_ready()["id"])
            registry.memory.remember("pending_reels", json.dumps({"library_asset":"one"}), "action")
            self.assertIsNone(registry.next_ready()); self.assertEqual("queued", registry.snapshot()[0]["status"])

    def test_rejects_bad_scene_pacing(self):
        with tempfile.TemporaryDirectory() as root:
            registry = self._registry(root, seconds=4)
            with self.assertRaisesRegex(ValueError, "5–10"):
                registry.episodes()

    def test_a_legacy_string_content_record_never_crashes_status_lookup(self):
        # Same historical-record gap as tests/test_dashboard.py and
        # tests/test_growth_pulse.py: a published_reels/pending_reels
        # record whose content parses to a bare string (not a dict) used
        # to crash this registry's own snapshot()/next_ready() with
        # AttributeError: 'str' object has no attribute 'get'.
        with tempfile.TemporaryDirectory() as root:
            registry = self._registry(root)
            registry.memory.remember(
                "pending_reels", json.dumps("a bare string record, not even an object"), "action",
            )
            registry.memory.remember(
                "published_reels", json.dumps("another bare string record"), "action",
            )
            self.assertEqual("one", registry.next_ready()["id"])
            self.assertEqual("ready", registry.snapshot()[0]["status"])
