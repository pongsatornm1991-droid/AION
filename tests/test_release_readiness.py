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
            for ident, episode_format in (("one", "illustrated-narrated-short"), ("two", "illustrated-narrated-short"), ("three", "illustrated-narrated-short"), ("four", "illustrated-narrated-short"), ("five", "illustrated-narrated-short"), ("six", "illustrated-narrated-short"), ("seven", "illustrated-narrated-short")):
                (root / "content" / "reels" / f"{ident}.mp4").write_bytes(b"video")
                (root / "content" / "reels" / f"{ident}-cover.png").write_bytes(b"cover")
                (root / "content" / "creator_series" / f"{ident}.json").write_text(json.dumps({
                    "id": ident, "series": "Test", "title": ident, "status": "production-ready-assets-and-script",
                    "format": episode_format, "target_duration_seconds": 50 if episode_format == "illustrated-narrated-short" else 120, "scene_seconds": 5,
                    "visual_style": {"id": "aion-neon-diorama-3d-v1", "approved": True},
                    "visual_qa": {"eligible": True, "reasons": []},
                    "audience_promise": "A clear evidence-led story with useful value for viewers of every age.",
                    "wonder_hook": "Could a surprising question change what we notice?", "creative_device": "journey",
                    "age_layers": {"children": "Ask.", "family": "Compare.", "deeper": "Check evidence."},
                    "science_boundary": "A boundary.", "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                    "scenes": [{"n": n, "visual": "The subject leads; AION is a guide.", "narration": "A useful narrated beat."} for n in range(1, 11 if episode_format == "illustrated-narrated-short" else 25)],
                }), encoding="utf-8")
            memory = MemoryEngine(root / "memory")
            for ident in ("one", "two", "three", "four", "five", "six", "seven"):
                memory.remember("youtube_creator_queue", json.dumps({
                    "episode_id": ident,
                    "quality_gate": {"eligible": True, "reasons": []},
                }), memory_type="action")
            report = ReleaseReadiness(memory, root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual("ready", report["state"])
            self.assertEqual(7, len(report["available"]["short"]))
            self.assertEqual("ready", report["shorts_buffer"]["state"])
            self.assertEqual(7, report["shorts_buffer"]["quality_ready"])

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

    def test_does_not_count_an_already_published_episode_as_available(self):
        # Regression for 2026-09-22: an episode's upload_status stays
        # "authorized-for-aion-publish" even after it is actually released
        # (publishing adds youtube.video_id; it does not change
        # upload_status), so the readiness check must not treat that field
        # alone as proof the episode is still available to publish.
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            series = root / "content" / "creator_series"; series.mkdir(parents=True)
            reels = root / "content" / "reels"; reels.mkdir(parents=True)
            (reels / "released.mp4").write_bytes(b"video")
            (reels / "released-cover.png").write_bytes(b"cover")
            (series / "released.json").write_text(json.dumps({
                "id": "released", "series": "Test", "title": "released", "status": "production-ready-assets-and-script",
                "format": "illustrated-narrated-short", "target_duration_seconds": 50, "scene_seconds": 5,
                "visual_style": {"id": "aion-neon-diorama-3d-v1", "approved": True},
                "visual_qa": {"eligible": True, "reasons": []},
                "audience_promise": "A clear evidence-led story with useful value for viewers of every age.",
                "wonder_hook": "Could a surprising question change what we notice?", "creative_device": "journey",
                "age_layers": {"children": "Ask.", "family": "Compare.", "deeper": "Check evidence."},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                "scenes": [{"n": n, "visual": "The subject leads; AION is a guide.", "narration": "A useful narrated beat."} for n in range(1, 11)],
            }), encoding="utf-8")
            memory = MemoryEngine(root / "memory")
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "released",
                "upload_status": "authorized-for-aion-publish",
                "youtube": {"video_id": "already-live-on-youtube"},
                "quality_gate": {"eligible": True, "reasons": []},
            }), memory_type="action")
            report = ReleaseReadiness(memory, root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual([], report["available"]["short"])

    def test_marks_an_upcoming_slot_early_when_the_buffer_is_empty(self):
        with tempfile.TemporaryDirectory() as root:
            report = ReleaseReadiness(MemoryEngine(Path(root) / "memory"), Path(root)).snapshot(
                datetime(2026, 9, 13, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )
            self.assertEqual("critical", report["state"])
            self.assertTrue(report["shortages"])
            self.assertEqual(7, report["shorts_buffer"]["missing"])
            self.assertEqual("ผลิตจากเรื่องใหม่ที่มีหลักฐานครบ", report["recovery_action"])
            self.assertEqual("urgent", report["early_warning"]["state"])
            self.assertIn("fast lane", report["early_warning"]["detail"])
