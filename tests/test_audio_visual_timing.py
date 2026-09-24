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
        # Rendered picture beats may extend through the bounded adaptive
        # window before narration is sent back for rewriting.
        self.assertEqual(3, report["minimum_extra_visual_beats"])
        self.assertIn("ย่อบท", report["detail"])

    def test_rejects_silent_final_scenes(self):
        report = AudioVisualTimingGate.assess(50, 60)
        self.assertFalse(report["eligible"])
        self.assertIn("narration-ends-before-final-scene", report["reasons"])
        self.assertEqual(10, report["trailing_silence_seconds"])
        self.assertIn("ห้ามประกอบคลิป", report["detail"])

    def test_allows_a_short_breath_when_scene_policy_explicitly_permits_it(self):
        report = AudioVisualTimingGate.assess(3.8, 5, max_trailing_silence=2.0)
        self.assertTrue(report["eligible"])
        self.assertEqual([], report["reasons"])

    def test_rejects_unreadable_audio_duration(self):
        report = AudioVisualTimingGate.assess(None, 120)
        self.assertFalse(report["eligible"])
        self.assertIn("invalid-audio", report["reasons"][0])

    def test_real_voice_extends_the_current_visual_without_speeding_it_up(self):
        report = AudioVisualTimingGate.plan_scene(5.4, 5)
        self.assertTrue(report["eligible"])
        self.assertEqual("extend-current-visual", report["action"])
        self.assertAlmostEqual(5.7, report["visual_seconds"])

    def test_extends_a_measured_naturally_long_line_without_cutting_voice_or_blocking_images(self):
        # Regression: the Maps Short's first selected voice measured 9.26s.
        # Its intentional 0.30s visual hold must not turn into a Studio stop.
        report = AudioVisualTimingGate.plan_scene(9.26, 5)
        self.assertTrue(report["eligible"])
        self.assertEqual("extend-current-visual", report["action"])
        self.assertAlmostEqual(9.56, report["visual_seconds"])

    def test_allows_a_measured_one_to_two_second_natural_hold_before_splitting(self):
        report = AudioVisualTimingGate.plan_scene(11.0, 5)
        self.assertTrue(report["eligible"])
        self.assertAlmostEqual(11.3, report["visual_seconds"])

    def test_returns_only_a_scene_beyond_the_bounded_adaptive_window_to_story(self):
        report = AudioVisualTimingGate.plan_scene(12.0, 5)
        self.assertFalse(report["eligible"])
        self.assertIn("narration-exceeds-safe-scene-window", report["reasons"])
