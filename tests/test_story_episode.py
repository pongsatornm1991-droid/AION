import os
import unittest
from unittest import mock

from tools import render_story_episode
from tools import render_story_episode_002


class StoryEpisodeTests(unittest.TestCase):
    def test_episode_uses_a_six_scene_storyboard(self):
        with mock.patch("tools.render_story_episode.render_reel", return_value="episode.mp4") as render:
            result = render_story_episode.render(output_dir="build")
        self.assertEqual("episode.mp4", result)
        kwargs = render.call_args.kwargs
        self.assertEqual(42, kwargs["duration"])
        self.assertEqual(6, len(kwargs["still_paths"]))
        self.assertEqual("#a78bfa", kwargs["mood"]["color"])
        self.assertTrue(render_story_episode.NARRATION.startswith("Before books"))
        self.assertTrue(os.path.basename(kwargs["still_paths"][0]).startswith("01-"))

    def test_second_episode_uses_five_seven_second_scenes(self):
        with mock.patch("tools.render_story_episode_002.render_reel", return_value="episode.mp4") as render:
            result = render_story_episode_002.render(output_dir="build")
        self.assertEqual("episode.mp4", result)
        kwargs = render.call_args.kwargs
        self.assertEqual(35, kwargs["duration"])
        self.assertEqual(5, len(kwargs["still_paths"]))
        self.assertEqual("#ffb86b", kwargs["mood"]["color"])


if __name__ == "__main__":
    unittest.main()
