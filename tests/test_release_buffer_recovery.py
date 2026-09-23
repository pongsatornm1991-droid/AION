import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

from brain.memory import MemoryEngine
from brain.release_readiness import ReleaseReadiness
from tools.recover_release_buffer import recover_once


class ReleaseBufferRecoveryTests(unittest.TestCase):
    @patch("tools.recover_release_buffer._active_by_kind", return_value={"short": []})
    @patch("tools.recover_release_buffer.StoryEpisodeStager")
    @patch("tools.recover_release_buffer.ResearchStoryHandoff")
    @patch("tools.recover_release_buffer.ResearchToStory")
    @patch("tools.recover_release_buffer.ReleaseReadiness")
    def test_recovery_batches_distinct_storyboards_up_to_the_safe_limit(self, readiness_cls, research_cls, handoff_cls, stager_cls, _active):
        readiness_cls.return_value.snapshot.return_value = {"shortages": [{"content_kind": "short", "missing": 7}]}
        research_cls.return_value.propose_batch.return_value = {"created_count": 5}
        handoff_cls.return_value.create_batch.return_value = {"created_count": 5}
        stager_cls.return_value.stage_batch.return_value = {"staged_episode_ids": ["one", "two", "three", "four", "five"]}

        report = recover_once(MagicMock(), Path("."))

        self.assertEqual("recovery-storyboards-prepared", report["stage"])
        self.assertTrue(report["needs_production"])
        self.assertEqual(5, report["prepared"][0]["requested"])
        research_cls.return_value.propose_batch.assert_called_once_with(limit=5)
        handoff_cls.return_value.create_batch.assert_called_once_with(limit=5)
        stager_cls.return_value.stage_batch.assert_called_once_with(limit=5, episode_format="short")

    def test_does_nothing_when_the_short_buffer_is_ready(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "content" / "creator_series").mkdir(parents=True)
            (root / "content" / "reels").mkdir(parents=True)
            for ident in ("one", "two", "three", "four", "five", "six", "seven"):
                (root / "content" / "reels" / f"{ident}.mp4").write_bytes(b"video")
                (root / "content" / "reels" / f"{ident}-cover.png").write_bytes(b"cover")
                (root / "content" / "creator_series" / f"{ident}.json").write_text(json.dumps({
                    "id": ident, "series": "Test", "title": ident, "status": "production-ready-assets-and-script",
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
            for ident in ("one", "two", "three", "four", "five", "six", "seven"):
                memory.remember("youtube_creator_queue", json.dumps({
                    "episode_id": ident,
                    "quality_gate": {"eligible": True, "reasons": []},
                }), memory_type="action")
            # The generic helper uses the actual current time; separately
            # ensure the fixture itself represents a valid ready buffer.
            self.assertEqual("ready", ReleaseReadiness(memory, root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )["state"])
            report = recover_once(memory, root)
            self.assertIn(report["stage"], {"buffer-already-ready", "recovery-needs-research"})
