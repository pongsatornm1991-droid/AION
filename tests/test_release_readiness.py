import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from brain.memory import MemoryEngine
from brain.release_readiness import ReleaseReadiness


class ReleaseReadinessTests(unittest.TestCase):
    def test_requires_distinct_ready_episodes_for_each_upcoming_short_slot(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "content" / "creator_series").mkdir(parents=True)
            (root / "content" / "reels").mkdir(parents=True)
            for ident in ("one", "two"):
                (root / "content" / "reels" / f"{ident}.mp4").write_bytes(b"video")
                (root / "content" / "reels" / f"{ident}-cover.png").write_bytes(b"cover")
                (root / "content" / "creator_series" / f"{ident}.json").write_text(json.dumps({
                    "id": ident, "series": "Test", "title": ident, "status": "production-ready-assets-and-script",
                    "format": "illustrated-narrated-short", "target_duration_seconds": 50, "scene_seconds": 5,
                    "audience_promise": "A clear evidence-led story with useful value for viewers of every age.",
                    "wonder_hook": "Could a surprising question change what we notice?", "creative_device": "journey",
                    "age_layers": {"children": "Ask.", "family": "Compare.", "deeper": "Check evidence."},
                    "science_boundary": "A boundary.", "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                    "scenes": [{"n": n, "visual": "The subject leads; AION is a guide.", "narration": "A useful narrated beat."} for n in range(1, 11)],
                }), encoding="utf-8")
            memory = MemoryEngine(root / "memory")
            for ident in ("one", "two"):
                memory.remember("youtube_creator_queue", json.dumps({
                    "episode_id": ident,
                    "quality_gate": {"eligible": True, "reasons": []},
                }), memory_type="action")
            report = ReleaseReadiness(memory, root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual("ready", report["state"])
            self.assertEqual(2, len(report["available"]["short"]))

    def test_does_not_count_a_video_without_a_saved_quality_gate(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            series = root / "content" / "creator_series"; series.mkdir(parents=True)
            reels = root / "content" / "reels"; reels.mkdir(parents=True)
            (reels / "unguarded.mp4").write_bytes(b"video")
            (reels / "unguarded-cover.png").write_bytes(b"cover")
            (series / "unguarded.json").write_text(json.dumps({
                "id": "unguarded", "series": "Test", "title": "unguarded", "status": "production-ready-assets-and-script",
                "format": "illustrated-narrated-short", "target_duration_seconds": 50, "scene_seconds": 5,
                "audience_promise": "A clear evidence-led story with useful value for viewers of every age.",
                "wonder_hook": "Could a surprising question change what we notice?", "creative_device": "journey",
                "age_layers": {"children": "Ask.", "family": "Compare.", "deeper": "Check evidence."},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                "scenes": [{"n": n, "visual": "The subject leads; AION is a guide.", "narration": "A useful narrated beat."} for n in range(1, 11)],
            }), encoding="utf-8")
            report = ReleaseReadiness(MemoryEngine(root / "memory"), root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual([], report["available"]["short"])

    def test_marks_an_upcoming_slot_early_when_the_buffer_is_empty(self):
        with tempfile.TemporaryDirectory() as root:
            report = ReleaseReadiness(MemoryEngine(Path(root) / "memory"), Path(root)).snapshot(
                datetime(2026, 9, 13, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual("attention", report["state"])
            self.assertTrue(report["shortages"])
