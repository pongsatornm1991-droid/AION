import unittest

from brain.audio_visual_timing import AudioVisualTimingGate


class AudioVisualTimingGateTests(unittest.TestCase):
    def test_allows_source_audio_that_fits_storyboard(self):
        report = AudioVisualTimingGate.assess(119.9, 120)
        self.assertTrue(report["eligible"])
        self.assertEqual("pass", report["state"])

    def test_rejects_audio_that_would_be_cut_by_final_video(self):
        report = AudioVisualTimingGate.assess(145.54, 120)
        self.assertFalse(report["eligible"])
        self.assertEqual("return-to-story", report["state"])
        self.assertEqual(6, report["minimum_extra_visual_beats"])
        self.assertIn("ย่อบท", report["detail"])

    def test_rejects_silent_final_scenes(self):
        report = AudioVisualTimingGate.assess(50, 60)
        self.assertFalse(report["eligible"])
        self.assertIn("narration-ends-before-final-scene", report["reasons"])
        self.assertEqual(10, report["trailing_silence_seconds"])
        self.assertIn("ห้ามประกอบคลิป", report["detail"])

    def test_rejects_unreadable_audio_duration(self):
        report = AudioVisualTimingGate.assess(None, 120)
        self.assertFalse(report["eligible"])
        self.assertIn("invalid-audio", report["reasons"][0])
