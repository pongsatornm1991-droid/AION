import unittest

from tools.reel_render import _duration_from_probe_text, _story_still_paths


class ReelRenderLibraryTests(unittest.TestCase):
    def test_reads_audio_duration_for_timing_gate(self):
        self.assertEqual(145.54, _duration_from_probe_text("Duration: 00:02:25.54, start: 0.0"))
        self.assertIsNone(_duration_from_probe_text("no duration here"))

    def test_science_topics_use_the_creator_scene_library(self):
        paths = _story_still_paths("A question about ocean life", "science and discovery")
        self.assertEqual(3, len(paths))
        self.assertTrue(any("aion-creator-scenes" in path for path in paths))

    def test_human_topics_use_the_creator_scene_library(self):
        paths = _story_still_paths("Listening to people", "community conversation")
        self.assertEqual(3, len(paths))
        self.assertTrue(all("aion-creator-scenes" in path for path in paths))
