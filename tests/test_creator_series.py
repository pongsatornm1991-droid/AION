import unittest

from brain.creator_series import CreatorSeriesRegistry


class CreatorSeriesTests(unittest.TestCase):
    def test_pilot_is_a_complete_long_form_storyboard(self):
        episodes = CreatorSeriesRegistry().episodes()
        self.assertEqual(1, len(episodes))
        self.assertEqual(24, len(episodes[0]["scenes"]))
        self.assertEqual(168, episodes[0]["target_duration_seconds"])
        self.assertEqual("production-ready-script", episodes[0]["status"])

