"""Regression checks for AION's fixed Bangkok publishing appointments."""

import unittest
from pathlib import Path


class YouTubeCreatorScheduleTests(unittest.TestCase):
    def test_has_four_day_shorts_first_cron(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "43 13 * * 0,4,5,6"', workflow)
        self.assertNotIn('cron: "15 13 * * 6"', workflow)

    def test_scheduled_release_lane_is_short(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertNotIn('SCHEDULE" == "15 13 * * 6"', workflow)
        self.assertIn('RELEASE_KIND="short"', workflow)
        self.assertIn('--content-kind "$RELEASE_KIND"', workflow)
