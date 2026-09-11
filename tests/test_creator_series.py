import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry


class CreatorSeriesTests(unittest.TestCase):
    def test_pilot_is_a_complete_long_form_storyboard(self):
        episodes = CreatorSeriesRegistry().episodes()
        # The program now contains the pilot plus two additional story
        # episodes.  Keep this assertion aligned with the actual curated
        # library while the per-episode checks below protect its quality.
        self.assertEqual(3, len(episodes))
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

    def test_rejects_a_story_without_audience_benefit_or_uncertainty_boundary(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            episode = {
                "id": "thin-story", "series": "Test", "title": "Thin story",
                "format": "illustrated-narrated-short", "scene_seconds": 5,
                "target_duration_seconds": 15, "status": "draft",
                "sources": [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}],
                "scenes": [
                    {"visual": "AION looks at a light", "narration": "One."},
                    {"visual": "AION walks onward", "narration": "Two."},
                    {"visual": "AION looks back", "narration": "Three."},
                ],
            }
            path = directory / "thin.json"
            path.write_text(json.dumps(episode), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "audience promise"):
                CreatorSeriesRegistry(root).episodes()

            episode["audience_promise"] = "This gives the viewer one grounded question worth carrying into their day."
            path.write_text(json.dumps(episode), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "wonder hook"):
                CreatorSeriesRegistry(root).episodes()

            episode.update({
                "wonder_hook": "Why does this small idea change what we notice?",
                "creative_device": "journey",
                "age_layers": {"children": "One simple image.", "family": "One shared question.", "deeper": "One evidence-bound interpretation."},
            })
            path.write_text(json.dumps(episode), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "uncertainty"):
                CreatorSeriesRegistry(root).episodes()
