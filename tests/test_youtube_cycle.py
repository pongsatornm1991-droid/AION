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

    def test_skips_a_blocked_reel_and_uploads_the_next_quality_gated_reel(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            reels = os.path.join(root, "content", "reels")
            os.makedirs(reels)
            for name in ("blocked.mp4", "ready.mp4"):
                with open(os.path.join(reels, name), "wb") as handle:
                    handle.write(b"video")
            memory.remember("published_reels", json.dumps({
                "video_path": "content/reels/blocked.mp4",
                "caption": "A reflective AION story with enough detail to be assessed by the quality gate.",
            }), memory_type="action", source="test", importance=1)
            memory.remember("published_reels", json.dumps({
                "video_path": "content/reels/ready.mp4",
                "caption": "A different reflective AION story with enough detail to be assessed by the quality gate.",
                "viewer_value": "Viewers receive a clear question that helps them examine an assumption.",
            }), memory_type="action", source="test", importance=1)
            uploader = lambda *_: {"video_id": "ready", "url": "https://youtu.be/ready", "privacy_status": "public"}
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}):
                report = YouTubeShortsCycle(memory, uploader=uploader).publish_once(repo_root=root)
            self.assertEqual("published", report["stage"])
            items = [json.loads(item["content"]) for item in memory.all("published_reels")]
            self.assertNotIn("youtube", items[0])
            self.assertEqual("ready", items[1]["youtube"]["video_id"])
