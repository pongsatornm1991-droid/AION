import json
import tempfile
import unittest
from datetime import datetime

from brain.growth_pulse import GrowthPulse
from brain.memory import MemoryEngine


class GrowthPulseTests(unittest.TestCase):
    def test_captures_channels_learning_and_only_once_per_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryEngine(temp_dir)
            memory.remember(
                category="social_feedback",
                content=json.dumps({"kind": "account", "followers_count": 42, "media_count": 7}),
                memory_type="observation",
                source="instagram-feedback",
            )
            memory.remember(
                category="published_reels",
                content=json.dumps({
                    "platform_actions": {"instagram": "ig-1", "facebook": "fb-1"},
                    "youtube": {"video_id": "yt-1"},
                }),
                memory_type="action",
                source="test",
            )

            now = lambda: datetime(2026, 9, 2, 8, 15)
            pulse = GrowthPulse(memory, now=now)
            report = pulse.capture_once()

            self.assertEqual("captured", report["stage"])
            self.assertEqual(42, report["instagram"]["followers_count"])
            self.assertEqual(
                {"instagram_reels": 1, "facebook_reels": 1, "youtube_shorts": 1},
                report["activity"],
            )
            self.assertEqual("already-reported", pulse.capture_once()["stage"])

