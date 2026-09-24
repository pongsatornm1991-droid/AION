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
            duration_reader=lambda _path: 9.8,
        )
        self.assertFalse(report["eligible"])
        self.assertIn("narration-exceeds-safe-scene-window", report["reasons"][0])

    def test_repairs_an_overlong_beat_before_any_image_work_and_remeasures_it(self):
        durations = iter((14.4, 6.7, 7.1))
        episode = {
            "id": "repairable",
            "scene_seconds": 5,
            "target_duration_seconds": 5,
            "scenes": [{
                "n": 1,
                "beat": "evidence",
                "visual": "AION studies a clear subject.",
                "narration": "The first observation establishes the cause. The second observation shows the effect clearly.",
            }],
        }

        report = NarrationPreflight.repair_episode_timing(
            episode,
            synthesize=lambda _text, _path: True,
            duration_reader=lambda _path: next(durations),
        )

        self.assertTrue(report["eligible"])
        self.assertEqual([1], report["timing_repair"]["repaired_scenes"])
        self.assertEqual(2, len(episode["scenes"]))
        self.assertEqual(10, episode["target_duration_seconds"])
        self.assertEqual("The first observation establishes the cause. The second observation shows the effect clearly.",
                         episode["scenes"][0]["narration_timing_repair"]["source_narration"])
        self.assertEqual([1, 2], [scene["n"] for scene in episode["scenes"]])
