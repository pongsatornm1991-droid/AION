import unittest

from brain.narration_preflight import NarrationPreflight


class NarrationPreflightTests(unittest.TestCase):
    def test_passes_when_actual_scene_voice_fits(self):
        report = NarrationPreflight.assess_episode(
            {"id": "fit", "scene_seconds": 5, "scenes": [{"narration": "A short clear line."}]},
            synthesize=lambda _text, _path: True,
            duration_reader=lambda _path: 4.7,
        )
        self.assertTrue(report["eligible"])
        self.assertEqual("pass", report["state"])

    def test_returns_story_when_actual_scene_voice_overruns(self):
        report = NarrationPreflight.assess_episode(
            {"id": "overrun", "scene_seconds": 5, "scenes": [{"narration": "A line that is too slow."}]},
            synthesize=lambda _text, _path: True,
            duration_reader=lambda _path: 5.3,
        )
        self.assertFalse(report["eligible"])
        self.assertEqual("return-to-story", report["state"])
        self.assertIn("scene-1:audio-overruns-storyboard", report["reasons"])

    def test_repairs_a_small_voice_timing_difference_automatically(self):
        durations = iter((5.3, 4.9))
        speeds = []

        def synthesize(_text, _path, speed=None):
            speeds.append(speed)
            return True

        report = NarrationPreflight.assess_episode(
            {"id": "repair", "scene_seconds": 5, "scenes": [{"narration": "A line."}]},
            synthesize=synthesize,
            duration_reader=lambda _path: next(durations),
        )
        self.assertTrue(report["eligible"])
        self.assertTrue(report["checks"][0]["auto_timed"])
        self.assertIsNone(speeds[0])
        self.assertGreater(speeds[1], 1)
