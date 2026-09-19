"""Regression checks for AION's fixed Bangkok publishing appointments."""

import unittest
from pathlib import Path


class YouTubeCreatorScheduleTests(unittest.TestCase):
    def test_has_separate_short_and_saturday_primary_crons(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "43 13 * * 0,4,5"', workflow)
        self.assertIn('cron: "15 13 * * 6"', workflow)

    def test_selects_long_form_for_the_saturday_appointment(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('SCHEDULE" == "15 13 * * 6"', workflow)
        self.assertIn('RELEASE_KIND="long-form"', workflow)
        self.assertIn('--content-kind "$RELEASE_KIND"', workflow)
