import unittest

from brain.youtube_quality import YouTubeQualityGate


class YouTubeQualityGateTests(unittest.TestCase):
    def test_requires_a_concrete_viewer_value(self):
        report = YouTubeQualityGate().assess({
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "visual_style": "illustrated-aion-storyboard-v4",
        })
        self.assertFalse(report["eligible"])
        self.assertIn("missing-explicit-viewer-value", report["reasons"])

    def test_rejects_duplicate_narrative_or_video(self):
        payload = {
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "viewer_value": "Viewers receive one grounded question and one honest uncertainty.",
            "visual_style": "illustrated-aion-storyboard-v4",
        }
        report = YouTubeQualityGate().assess(payload, [payload])
        self.assertFalse(report["eligible"])
        self.assertIn("duplicate-video", report["reasons"])

    def test_marks_unknown_visual_style_for_disclosure_review(self):
        report = YouTubeQualityGate().assess({
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "viewer_value": "Viewers receive one grounded question and one honest uncertainty.",
        })
        self.assertTrue(report["eligible"])
        self.assertTrue(report["ai_disclosure_review"])
