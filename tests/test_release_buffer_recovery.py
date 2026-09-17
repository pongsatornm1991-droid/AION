import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from brain.memory import MemoryEngine
from brain.release_readiness import ReleaseReadiness
from tools.recover_release_buffer import recover_once


class ReleaseBufferRecoveryTests(unittest.TestCase):
    def test_does_nothing_when_the_short_buffer_is_ready(self):
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
            # The generic helper uses the actual current time; separately
            # ensure the fixture itself represents a valid ready buffer.
            self.assertEqual("ready", ReleaseReadiness(memory, root).snapshot(
                datetime(2026, 9, 14, 9, 0, tzinfo=ReleaseReadiness.BANGKOK)
            )["state"])
            report = recover_once(memory, root)
            self.assertIn(report["stage"], {"buffer-already-ready", "recovery-needs-research"})
