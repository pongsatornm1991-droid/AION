"""Regression checks for AION's fixed Bangkok publishing appointments."""

import unittest
from pathlib import Path


class YouTubeCreatorScheduleTests(unittest.TestCase):
    def test_has_daily_shorts_first_cron(self):
        # Scaled from a 4-day (Thu-Sun) to a daily cadence on 2026-09-21,
        # once creator-scene-production.yml also became a daily shift.
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 13 * * *"', workflow)
        self.assertNotIn('cron: "15 13 * * 6"', workflow)

    def test_scheduled_release_lane_is_short(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertNotIn('SCHEDULE" == "15 13 * * 6"', workflow)
        self.assertIn('RELEASE_KIND="short"', workflow)
        self.assertIn('--content-kind "$RELEASE_KIND"', workflow)
        self.assertIn('episode_id:', workflow)
        self.assertIn('quality-youtube-creator', workflow)
        self.assertIn('Stage: published', workflow)
