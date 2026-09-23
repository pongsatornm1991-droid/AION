import unittest

from brain.youtube_quality import YouTubeQualityGate


class YouTubeQualityGateTests(unittest.TestCase):
    def test_requires_a_concrete_viewer_value(self):
        report = YouTubeQualityGate().assess({
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "visual_style": "aion-neon-diorama-3d-v1",
        })
        self.assertFalse(report["eligible"])
        self.assertIn("missing-explicit-viewer-value", report["reasons"])

    def test_rejects_duplicate_narrative_or_video(self):
        payload = {
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "viewer_value": "Viewers receive one grounded question and one honest uncertainty.",
            "visual_style": "aion-neon-diorama-3d-v1",
        }
        report = YouTubeQualityGate().assess(payload, [payload])
        self.assertFalse(report["eligible"])
        self.assertIn("duplicate-video", report["reasons"])

    def test_blocks_unknown_visual_style_from_automatic_release(self):
        report = YouTubeQualityGate().assess({
            "video_path": "content/reels/a.mp4",
            "caption": "AION explores how a small observation can change the way we ask a larger question.",
            "viewer_value": "Viewers receive one grounded question and one honest uncertainty.",
        })
        self.assertFalse(report["eligible"])
        self.assertIn("visual-style-not-channel-signature", report["reasons"])
        self.assertTrue(report["ai_disclosure_review"])

    def test_blocks_a_new_video_about_the_same_specific_topic(self):
        base = {
            "caption": "AION explains an evidence-led idea in a useful way for viewers.",
            "viewer_value": "Viewers receive a grounded explanation with a clear uncertainty boundary.",
            "visual_style": "aion-neon-diorama-3d-v1",
        }
        candidate = {**base, "video_path": "content/reels/new.mp4", "title": "How yakhchāls kept ice", "topic_key": "Persian yakhchal ice storage"}
        earlier = {**base, "video_path": "content/reels/old.mp4", "title": "Yakhchal desert ice", "topic_key": "Persian yakhchal ice storage", "youtube": {"video_id": "old"}}
        report = YouTubeQualityGate().assess(candidate, [earlier])
        self.assertFalse(report["eligible"])
        self.assertIn("duplicate-topic", report["reasons"])
