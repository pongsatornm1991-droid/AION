import json
import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.youtube_audience import YouTubeAudienceCycle


class YouTubeAudienceTests(unittest.TestCase):
    def test_records_changed_public_metrics_for_aions_own_video(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("youtube_creator_queue", json.dumps({"youtube": {"video_id": "abc"}}), "action")
            cycle = YouTubeAudienceCycle(memory, statistics_reader=lambda ids: [{"video_id": "abc", "title": "AION test", "view_count": "12", "like_count": "2", "comment_count": "1"}])
            self.assertEqual("captured", cycle.capture_once()["stage"])
            stored = json.loads(memory.all("social_feedback")[0]["content"])
            self.assertEqual(12, stored["view_count"])
            self.assertIn("Retention", stored["epistemic_boundary"])
            self.assertEqual("no-changes", cycle.capture_once()["stage"])

    def test_does_not_claim_metrics_without_published_video(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual("no-published-aion-youtube-video", YouTubeAudienceCycle(MemoryEngine(root)).capture_once()["stage"])
