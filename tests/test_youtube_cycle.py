import json
import os
import tempfile
import unittest
from unittest.mock import patch

from brain.memory import MemoryEngine
from brain.youtube import YouTubeShortsCycle


class YouTubeShortsCycleTests(unittest.TestCase):
    def test_uploads_one_completed_reel_and_remembers_the_video(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            os.makedirs(os.path.join(root, "content", "reels"))
            video = os.path.join(root, "content", "reels", "aion.mp4")
            with open(video, "wb") as handle:
                handle.write(b"video")
            memory.remember(
                "published_reels", json.dumps({
                    "video_path": "content/reels/aion.mp4",
                    "caption": "AION remembers how a small record can help us ask what should be carried into tomorrow.",
                    "viewer_value": "Viewers receive one reflective question and an honest reason to examine their own records.",
                    "visual_style": "illustrated-aion-storyboard-v4", "language": "en",
                }),
                memory_type="action", source="test", importance=1,
            )
            calls = []
            cycle = YouTubeShortsCycle(memory, uploader=lambda *args: calls.append(args) or {"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "private"})
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}):
                report = cycle.publish_once(repo_root=root)
            self.assertEqual(report["stage"], "published")
            self.assertEqual(len(calls), 1)
            payload = json.loads(memory.all("published_reels")[0]["content"])
            self.assertEqual(payload["youtube"]["video_id"], "abc")
            self.assertEqual(cycle.publish_once(repo_root=root)["stage"], "no-pending")

    def test_does_not_mark_reel_uploaded_after_failure(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "published_reels", json.dumps({
                    "video_path": "missing.mp4",
                    "caption": "AION asks how a small observation can become a careful question without pretending to know too much.",
                    "viewer_value": "Viewers receive one careful question and a clear boundary on what the episode cannot prove.",
                    "visual_style": "illustrated-aion-storyboard-v4",
                }),
                memory_type="action", source="test", importance=1,
            )
            report = YouTubeShortsCycle(memory, uploader=lambda *args: (_ for _ in ()).throw(RuntimeError("no access"))).publish_once(repo_root=root)
            self.assertEqual(report["stage"], "quality-review-required")
            self.assertNotIn("youtube", json.loads(memory.all("published_reels")[0]["content"]))
