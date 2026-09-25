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
        self.assertGreaterEqual(len(episodes), 3)
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

    def test_roman_longform_is_a_true_widescreen_length_storyboard(self):
        episode = next(item for item in CreatorSeriesRegistry().episodes() if item["id"] == "aion-wonders-003")
        self.assertEqual(40, len(episode["scenes"]))
        self.assertEqual(200, episode["target_duration_seconds"])
        self.assertEqual(5, episode["scene_seconds"])
        self.assertEqual("fast-cut-subject-first-v1", episode["pacing_policy"])

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

    def test_skip_invalid_excludes_one_bad_episode_without_blocking_the_others(self):
        # Regression for 2026-09-25: a single malformed episode file made
        # CreatorSeriesRegistry.episodes() raise before returning anything,
        # which crashed the whole Studio shift and starved every other ready
        # episode behind it, not just the broken one (found live: 4
        # consecutive creator-scene-production.yml failures while the Shorts
        # buffer sat at 0/7). skip_invalid must exclude only the bad file.
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            good = {
                "id": "good-episode", "series": "Test", "title": "Good",
                "format": "illustrated-narrated-short", "scene_seconds": 5,
                "target_duration_seconds": 15, "status": "storyboard-ready-needs-assets",
                "audience_promise": "This gives the viewer one grounded question worth carrying into their day.",
                "wonder_hook": "Why does this small idea change what we notice?",
                "creative_device": "journey",
                "age_layers": {"children": "One simple image.", "family": "One shared question.", "deeper": "One evidence-bound interpretation."},
                "science_boundary": "A boundary.",
                "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                "scenes": [
                    {"visual": "AION looks at a light", "narration": "One."},
                    {"visual": "AION walks onward", "narration": "Two."},
                    {"visual": "AION looks back", "narration": "Three."},
                ],
            }
            bad = {**good, "id": "bad-episode", "audience_promise": "Too short."}
            (directory / "good.json").write_text(json.dumps(good), encoding="utf-8")
            (directory / "bad.json").write_text(json.dumps(bad), encoding="utf-8")

            registry = CreatorSeriesRegistry(root)
            with self.assertRaises(ValueError):
                registry.episodes()

            episodes = registry.episodes(skip_invalid=True)

            self.assertEqual(["good-episode"], [item["id"] for item in episodes])
            self.assertEqual(1, len(registry.invalid))
            self.assertEqual("bad-episode", registry.invalid[0]["id"])
            self.assertIn("audience promise", registry.invalid[0]["reason"])
