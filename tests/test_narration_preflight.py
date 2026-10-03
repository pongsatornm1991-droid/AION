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
            duration_reader=lambda _path: 12.0,
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
            "visual_narrative": {"scene_progression": ["evidence"]},
            "fact_first_visual": {"scene_roles": [{"n": 1, "beat": "evidence", "role": "evidence"}]},
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
        self.assertEqual([scene["beat"] for scene in episode["scenes"]],
                         episode["visual_narrative"]["scene_progression"])
        self.assertEqual(2, len(episode["fact_first_visual"]["scene_roles"]))

    def test_uses_a_second_bounded_pass_only_for_a_different_untouched_beat(self):
        durations = iter((14.4, 6.0, 6.7, 7.1, 12.0, 6.7, 7.1, 12.0, 6.0, 5.8, 5.7, 5.6))
        episode = {
            "id": "two-repairs",
            "scene_seconds": 5,
            "target_duration_seconds": 10,
            "scenes": [
                {"n": 1, "beat": "first", "visual": "AION studies the first subject.",
                 "narration": "The first observation establishes the cause. The first observation shows the effect clearly."},
                {"n": 2, "beat": "second", "visual": "AION studies the second subject.",
                 "narration": "The second observation establishes the cause. The second observation shows the effect clearly."},
            ],
        }

        report = NarrationPreflight.repair_episode_timing(
            episode, synthesize=lambda _text, _path: True, duration_reader=lambda _path: next(durations)
        )

        self.assertTrue(report["eligible"])
        self.assertEqual(4, len(episode["scenes"]))
        self.assertEqual(20, episode["target_duration_seconds"])
        self.assertEqual([1], report["timing_repair"]["initial_repaired_scenes"])
        self.assertEqual([3], report["timing_repair"]["repaired_scenes"])

    # Owner, 2026-10-03: rather than trim an 82-word line to fit one beat,
    # "เพิ่มฉากเข้าไปให้พอดีคำ" -- add as many scenes as the measured voice
    # needs, each aimed at ~8 seconds so the cut stays fast.
    LONG_LINE = (
        "Breathing changes during exertion because the body tunes how deep and how fast you breathe to keep oxygen "
        "and carbon dioxide steady. When breathing swings too high or too low, carbon dioxide and acidity shift and "
        "it can feel distressing. Slow, paced breathing with pursed lips can make each breath work better and help "
        "you recover after effort."
    )

    def test_parts_needed_scales_with_measured_voice_length(self):
        self.assertEqual(2, NarrationPreflight._parts_needed(14.4))
        self.assertEqual(5, NarrationPreflight._parts_needed(33.0))
        self.assertEqual(NarrationPreflight.MAX_SPLIT_PARTS, NarrationPreflight._parts_needed(500))
        self.assertEqual(2, NarrationPreflight._parts_needed(None))

    def test_split_narration_returns_the_requested_number_of_whole_word_pieces(self):
        for parts in (2, 3, 4):
            pieces = NarrationPreflight._split_narration(self.LONG_LINE, parts)
            self.assertEqual(parts, len(pieces))
            self.assertEqual(self.LONG_LINE.split(), " ".join(pieces).split())

    def test_a_very_long_beat_becomes_as_many_scenes_as_its_voice_needs(self):
        # 33s of voice cannot be held on one picture (12s ceiling) and one
        # split (2 x 16s) still would not fit -- this used to fail the whole
        # episode ("return-to-story") and block image production.
        durations = {}

        def reader(path):
            narration_words = durations[path]
            return narration_words * 0.5

        def synthesize(text, path):
            durations[path] = len(text.split())
            return True

        episode = {
            "id": "long", "scene_seconds": 5, "target_duration_seconds": 5,
            "scenes": [{"n": 1, "beat": "connection", "visual": "AION studies a clear subject.", "narration": self.LONG_LINE}],
            "visual_narrative": {"scene_progression": ["connection"]},
            "fact_first_visual": {"scene_roles": [{"n": 1, "beat": "connection", "role": "evidence"}]},
        }
        # 58 words * 0.5 = 29s -> ceil(29.3 / 8) = 4 scenes of ~14 words (~7s).
        report = NarrationPreflight.repair_episode_timing(
            episode, synthesize=synthesize, duration_reader=reader
        )
        self.assertTrue(report["eligible"], report["reasons"])
        self.assertEqual(4, len(episode["scenes"]))
        self.assertEqual(self.LONG_LINE.split(), " ".join(s["narration"] for s in episode["scenes"]).split())
        self.assertEqual(
            ["connection—setup", "connection—continuation", "connection—continuation-3", "connection—continuation-4"],
            [s["beat"] for s in episode["scenes"]],
        )
        self.assertEqual([1, 2, 3, 4], [s["n"] for s in episode["scenes"]])
        self.assertEqual(20, episode["target_duration_seconds"])
        self.assertEqual([s["beat"] for s in episode["scenes"]], episode["visual_narrative"]["scene_progression"])
        self.assertEqual(4, len(episode["fact_first_visual"]["scene_roles"]))
        self.assertEqual(4, episode["scenes"][0]["narration_timing_repair"]["parts"])

