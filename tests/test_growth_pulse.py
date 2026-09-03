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

    def test_a_legacy_string_action_record_never_crashes_the_pulse(self):
        # Some historical published_reels records predate the multi-platform
        # {"instagram": ..., "facebook": ...} action shape and stored a
        # single action id/string under "action" instead of a dict. A real
        # production run hit exactly this and crashed with
        # AttributeError: 'str' object has no attribute 'get'.
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryEngine(temp_dir)
            memory.remember(
                category="published_reels",
                content=json.dumps({"action": "some-legacy-action-id"}),
                memory_type="action",
                source="test",
            )
            memory.remember(
                category="published_reels",
                content=json.dumps({
                    "platform_actions": {"instagram": "ig-2"},
                    "youtube": "not-a-dict-either",
                }),
                memory_type="action",
                source="test",
            )
            memory.remember(
                category="published_reels",
                content=json.dumps("a bare string record, not even an object"),
                memory_type="action",
                source="test",
            )

            pulse = GrowthPulse(memory, now=lambda: datetime(2026, 9, 3, 8, 0))
            report = pulse.capture_once()

            self.assertEqual("captured", report["stage"])
            self.assertEqual(
                {"instagram_reels": 1, "facebook_reels": 0, "youtube_shorts": 0},
                report["activity"],
            )


if __name__ == "__main__":
    unittest.main()
