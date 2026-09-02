import unittest

from brain.creator_series import CreatorSeriesRegistry


class CreatorSeriesTests(unittest.TestCase):
    def test_pilot_is_a_complete_long_form_storyboard(self):
        episodes = CreatorSeriesRegistry().episodes()
        self.assertEqual(2, len(episodes))
        pilot = next(item for item in episodes if item["id"] == "aion-wonders-001")
        self.assertEqual(24, len(pilot["scenes"]))
        self.assertEqual(168, pilot["target_duration_seconds"])
        self.assertEqual("production-ready-script", pilot["status"])

    def test_illustrated_short_has_real_assets_and_safe_pacing(self):
        episode = next(
            item for item in CreatorSeriesRegistry().episodes()
            if item["id"] == "aion-wonders-002"
        )
        self.assertEqual("illustrated-narrated-short", episode["format"])
        self.assertEqual(4, len(episode["scenes"]))
        self.assertEqual(9, episode["scene_seconds"])
        self.assertEqual(36, episode["target_duration_seconds"])
        self.assertEqual(2, len(episode["sources"]))
