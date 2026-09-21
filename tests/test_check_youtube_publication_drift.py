import json
import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from tools.check_youtube_publication_drift import find_drift, notify, recorded_video_ids


class YouTubePublicationDriftTests(unittest.TestCase):
    def _memory_with_one_recorded_video(self, root):
        memory = MemoryEngine(root=root)
        memory.remember("youtube_creator_queue", json.dumps({
            "episode_id": "aion-wonders-005-venus-flytrap-counts",
            "youtube": {"video_id": "known123", "url": "https://youtube.com/shorts/known123",
                        "privacy_status": "public"},
        }))
        return memory

    def test_recorded_video_ids_reads_the_real_queue_schema(self):
        with tempfile.TemporaryDirectory() as root:
            memory = self._memory_with_one_recorded_video(root)
            self.assertEqual(
                {"known123": "aion-wonders-005-venus-flytrap-counts"},
                recorded_video_ids(memory),
            )

    def test_a_channel_video_with_no_memory_record_is_flagged_as_orphaned(self):
        """Regression: this is exactly the condition three real episodes were
        found in this session -- genuinely public on YouTube, with the Studio
        queue never having learned they existed at all."""
        with tempfile.TemporaryDirectory() as root:
            memory = self._memory_with_one_recorded_video(root)
            channel_videos = [
                {"video_id": "known123", "title": "Already tracked", "privacy_status": "public"},
                {"video_id": "mystery456", "title": "Never reconciled", "privacy_status": "public"},
            ]
            report = find_drift(memory, channel_videos)
            self.assertEqual(1, report["orphaned_video_count"])
            self.assertEqual("mystery456", report["orphaned_videos"][0]["video_id"])
            self.assertEqual(2, report["channel_video_count"])
            self.assertEqual(1, report["recorded_video_count"])

    def test_no_drift_when_every_channel_video_is_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            memory = self._memory_with_one_recorded_video(root)
            report = find_drift(memory, [{"video_id": "known123", "title": "Tracked"}])
            self.assertEqual(0, report["orphaned_video_count"])
            self.assertEqual([], report["orphaned_videos"])

    def test_notify_does_nothing_without_telegram_credentials(self):
        import os
        original = dict(os.environ)
        try:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            os.environ.pop("TELEGRAM_CHAT_ID", None)
            self.assertFalse(notify([{"video_id": "x", "title": "y", "privacy_status": "public"}]))
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_notify_never_raises_even_when_the_request_fails(self):
        import os
        original = dict(os.environ)
        try:
            os.environ["TELEGRAM_BOT_TOKEN"] = "fake-token"
            os.environ["TELEGRAM_CHAT_ID"] = "fake-chat"
            # No real network in this sandbox -- the point is that a failed
            # send is swallowed, never raised, so the detector's own exit
            # status still reflects the comparison, not a Telegram outage.
            result = notify([{"video_id": "x", "title": "y", "privacy_status": "public"}])
            self.assertIn(result, (True, False))
        finally:
            os.environ.clear()
            os.environ.update(original)


if __name__ == "__main__":
    unittest.main()
