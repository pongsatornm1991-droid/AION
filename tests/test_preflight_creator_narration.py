import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.preflight_creator_narration import blocks_everything, preflight


class PreflightCreatorNarrationTests(unittest.TestCase):
    def test_one_invalid_episode_does_not_block_narration_preflight_on_the_others(self):
        # Regression for 2026-09-25: creator-scene-production.yml failed
        # here (before ever reaching image generation) because
        # CreatorSeriesRegistry.episodes() raised on a single episode that
        # currently fails a content-policy check, which crashed this
        # preflight for every other ready storyboard too.
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            good = {
                "id": "good", "series": "A", "title": "Episode", "status": "storyboard-ready-needs-assets",
                "format": "illustrated-narrated-short", "scene_seconds": 5, "target_duration_seconds": 15,
                "audience_promise": "A clear benefit for curious viewers of every age.", "wonder_hook": "Why does this happen?",
                "creative_device": "journey", "age_layers": {"children": "Ask", "family": "Talk", "deeper": "Test"},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one"}, {"url": "https://two"}],
                "scenes": [{"n": n, "visual": "AION explores.", "narration": "AION asks."} for n in range(3)],
            }
            bad = {**good, "id": "bad", "audience_promise": "Too short.", "status": "storyboard-ready-needs-assets"}
            (directory / "good.json").write_text(json.dumps(good), encoding="utf-8")
            (directory / "bad.json").write_text(json.dumps(bad), encoding="utf-8")

            with patch(
                "tools.preflight_creator_narration.NarrationPreflight.repair_episode_timing",
                return_value={"eligible": True, "episode_id": "good", "scene_durations": [5, 5, 5]},
            ) as repair:
                result = preflight(root=root)

            self.assertTrue(result["eligible"])
            self.assertEqual(1, len(result["reports"]))
            self.assertEqual(["good"], [call.args[0]["id"] for call in repair.call_args_list])

    def test_write_timeline_persists_the_repair_synced_planning_ledgers(self):
        # Regression for 2026-09-25: NarrationPreflight.repair_episode_timing
        # updates episode["visual_narrative"]["scene_progression"] and
        # episode["fact_first_visual"]["scene_roles"] IN PLACE after a scene
        # split, but this write-back re-read the episode fresh from disk and
        # only copied scenes/target_duration_seconds/narration_timing_repairs
        # -- silently dropping the synced fields. A real episode got
        # permanently stuck this way: VisualNarrativeGate and
        # FactFirstVisualGate kept rejecting it on every later run because
        # scene_progression/scene_roles still had the pre-split scene count,
        # and the only code path that could fix them (this one) could never
        # even reach the episode once CreatorSeriesRegistry.episodes() (used
        # at the top of this same preflight) started raising on it.
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            episode = {
                "id": "repairable", "series": "A", "title": "Episode", "status": "storyboard-ready-needs-assets",
                "format": "illustrated-narrated-short", "scene_seconds": 5, "target_duration_seconds": 15,
                "audience_promise": "A clear benefit for curious viewers of every age.", "wonder_hook": "Why does this happen?",
                "creative_device": "journey", "age_layers": {"children": "Ask", "family": "Talk", "deeper": "Test"},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one"}, {"url": "https://two"}],
                "scenes": [
                    {"n": 1, "beat": "evidence", "visual": "AION studies a clear subject.", "narration": "One long observation."},
                    {"n": 2, "beat": "boundary", "visual": "AION notes a limit.", "narration": "A boundary beat."},
                    {"n": 3, "beat": "takeaway", "visual": "AION shares the takeaway.", "narration": "A takeaway beat."},
                ],
                "visual_narrative": {"scene_progression": ["evidence", "boundary", "takeaway"]},
                "fact_first_visual": {"scene_roles": [
                    {"n": 1, "beat": "evidence", "role": "evidence"},
                    {"n": 2, "beat": "boundary", "role": "boundary"},
                    {"n": 3, "beat": "takeaway", "role": "takeaway"},
                ]},
            }
            (directory / "repairable.json").write_text(json.dumps(episode), encoding="utf-8")

            def fake_split_repair(ep, *args, **kwargs):
                # Simulate splitting scene 1 ("evidence") into two, the way a
                # real overlong beat is repaired -- everything after it shifts.
                ep["scenes"] = [
                    {"n": 1, "beat": "evidence-a", "visual": "AION studies the first half.", "narration": "First half."},
                    {"n": 2, "beat": "evidence-b", "visual": "AION studies the second half.", "narration": "Second half."},
                    {"n": 3, "beat": "boundary", "visual": "AION notes a limit.", "narration": "A boundary beat."},
                    {"n": 4, "beat": "takeaway", "visual": "AION shares the takeaway.", "narration": "A takeaway beat."},
                ]
                ep["target_duration_seconds"] = 20
                ep["visual_narrative"]["scene_progression"] = ["evidence-a", "evidence-b", "boundary", "takeaway"]
                ep["fact_first_visual"]["scene_roles"] = [
                    {"n": 1, "beat": "evidence-a", "role": "evidence"},
                    {"n": 2, "beat": "evidence-b", "role": "evidence"},
                    {"n": 3, "beat": "boundary", "role": "boundary"},
                    {"n": 4, "beat": "takeaway", "role": "takeaway"},
                ]
                return {"eligible": True, "episode_id": ep["id"], "scene_durations": [5.0, 5.0, 5.0, 5.0]}

            with patch(
                "tools.preflight_creator_narration.NarrationPreflight.repair_episode_timing",
                side_effect=fake_split_repair,
            ):
                preflight(root=root, write_timeline=True)

            saved = json.loads((directory / "repairable.json").read_text(encoding="utf-8"))
            self.assertEqual(
                ["evidence-a", "evidence-b", "boundary", "takeaway"],
                saved["visual_narrative"]["scene_progression"],
            )
            self.assertEqual(4, len(saved["fact_first_visual"]["scene_roles"]))

    def test_one_unfittable_storyboard_is_flagged_and_does_not_block_the_others(self):
        # Regression for 2026-10-03: a single storyboard with an 82-word
        # connection beat failed `--require-eligible` for the whole batch, so
        # image production stopped for every ready storyboard for two days.
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            base = {
                "series": "A", "title": "Episode", "status": "storyboard-ready-needs-assets",
                "format": "illustrated-narrated-short", "scene_seconds": 5, "target_duration_seconds": 15,
                "audience_promise": "A clear benefit for curious viewers of every age.", "wonder_hook": "Why does this happen?",
                "creative_device": "journey", "age_layers": {"children": "Ask", "family": "Talk", "deeper": "Test"},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one"}, {"url": "https://two"}],
                "scenes": [{"n": n, "visual": "AION explores.", "narration": "AION asks."} for n in range(3)],
            }
            for name in ("fits", "too-long"):
                (directory / f"{name}.json").write_text(json.dumps({**base, "id": name}), encoding="utf-8")

            def repair(episode, *args, **kwargs):
                if episode["id"] == "too-long":
                    return {"eligible": False, "episode_id": "too-long", "reasons": ["scene-9:narration-exceeds-safe-scene-window"]}
                return {"eligible": True, "episode_id": "fits", "scene_durations": [5, 5, 5]}

            with patch("tools.preflight_creator_narration.NarrationPreflight.repair_episode_timing", side_effect=repair):
                result = preflight(root=root, write_timeline=True)
                again = preflight(root=root, write_timeline=True)

            self.assertEqual(["fits"], result["ready_for_images"])
            self.assertEqual(["too-long"], result["blocked"])
            self.assertFalse(blocks_everything(result))
            flagged = json.loads((directory / "too-long.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {"eligible": False, "reasons": ["scene-9:narration-exceeds-safe-scene-window"]},
                flagged["narration_preflight"],
            )
            fits = json.loads((directory / "fits.json").read_text(encoding="utf-8"))
            self.assertNotIn("narration_preflight", fits)
            self.assertEqual("audio-driven-v1", fits["audio_visual_timeline"]["version"])
            self.assertEqual(result["blocked"], again["blocked"])

    def test_the_step_still_fails_loudly_when_nothing_can_start_image_production(self):
        self.assertTrue(blocks_everything({"blocked": ["a"], "ready_for_images": []}))
        self.assertFalse(blocks_everything({"blocked": [], "ready_for_images": []}))
        self.assertFalse(blocks_everything({"blocked": ["a"], "ready_for_images": ["b"]}))

