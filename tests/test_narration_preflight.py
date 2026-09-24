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

    def test_extends_visual_when_actual_scene_voice_overruns_authored_beat(self):
        report = NarrationPreflight.assess_episode(
            {"id": "overrun", "scene_seconds": 5, "scenes": [{"narration": "A line that is too slow."}]},
            synthesize=lambda _text, _path: True,
            duration_reader=lambda _path: 5.3,
        )
        self.assertTrue(report["eligible"])
        self.assertEqual("pass", report["state"])
        self.assertAlmostEqual(5.6, report["scene_durations"][0])

    def test_does_not_change_voice_speed_to_fit_an_authored_beat(self):
        durations = iter((5.3,))
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
        self.assertAlmostEqual(5.6, report["checks"][0]["visual_seconds"])
        self.assertIsNone(speeds[0])
        self.assertEqual(1, len(speeds))

    def test_returns_story_only_when_a_scene_exceeds_safe_visual_hold(self):
        report = NarrationPreflight.assess_episode(
            {"id": "long", "scene_seconds": 5, "scenes": [{"narration": "A line that cannot fit."}]},
            synthesize=lambda _text, _path: True,
            duration_reader=lambda _path: 9.3,
        )
        self.assertFalse(report["eligible"])
        self.assertIn("narration-exceeds-safe-scene-window", report["reasons"][0])
