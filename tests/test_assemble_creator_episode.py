import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools.assemble_creator_episode import _write_subtitles, assemble_once, backfill_subtitles_once


class AssembleCreatorEpisodeTests(unittest.TestCase):
    def test_subtitles_follow_renderer_scene_extensions(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "episode.mp4"
            output.write_bytes(b"mp4")
            output.with_suffix(".timing.json").write_text(
                json.dumps({"scene_durations": [5.5, 5.0]}), encoding="utf-8"
            )
            episode = {"scene_seconds": 5, "scenes": [
                {"narration": "First."}, {"narration": "Second."},
            ]}
            subtitle = _write_subtitles(episode, output)
            text = subtitle.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:05,500", text)
            self.assertIn("00:00:05,500 --> 00:00:10,500", text)

    def test_assembles_every_scene_then_advances_only_that_episode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            assets = root / "assets" / "content-library" / "aion-stories" / "episode"; assets.mkdir(parents=True)
            for number in (1, 2, 3): (assets / f"{number:02d}.png").write_bytes(b"png")
            payload = {"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"An evidence-led story useful to every age.","wonder_hook":"Could this test work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"assets-ready-for-assembly","scenes":[{"n":1,"beat":"hook","visual":"AION explores.","narration":"One.","image":"assets/content-library/aion-stories/episode/01.png"},{"n":2,"beat":"reveal","visual":"AION observes.","narration":"Two.","image":"assets/content-library/aion-stories/episode/02.png"},{"n":3,"beat":"end","visual":"AION asks.","narration":"Three.","image":"assets/content-library/aion-stories/episode/03.png"}]}
            source = episode_dir / "episode.json"; source.write_text(json.dumps(payload), encoding="utf-8")
            def renderer(_, __, output, **kwargs):
                self.assertEqual(15, kwargs["duration"]); self.assertEqual(3, len(kwargs["still_paths"]))
                self.assertIsNone(kwargs["motion_paths"])
                self.assertEqual((1080, 1920), kwargs["frame_size"])
                Path(output).parent.mkdir(parents=True, exist_ok=True); Path(output).write_bytes(b"mp4")
            # This test isolates orchestration.  The renderer fixture writes
            # only a marker file, so the real media gate is intentionally
            # mocked; dedicated video-quality tests cover the gate itself.
            with mock.patch.dict("os.environ", {"AION_REQUIRE_MOTION_VIDEO": "false"}):
                with mock.patch("tools.assemble_creator_episode.VideoQualityGate.assess", return_value={"eligible": True}):
                    result = assemble_once(root, renderer=renderer)
            self.assertEqual("episode-rendered-for-quality", result["stage"])
            self.assertTrue((root / result["subtitle_path"]).is_file())
            self.assertIn("00:00:00,000 --> 00:00:05,000", (root / result["subtitle_path"]).read_text(encoding="utf-8"))
            self.assertEqual("production-ready-assets-and-script", json.loads(source.read_text(encoding="utf-8"))["status"])

    def test_prefers_complete_automatic_motion_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            assets = root / "assets" / "content-library" / "aion-stories" / "episode"; assets.mkdir(parents=True)
            for number in (1, 2, 3):
                (assets / f"{number:02d}.png").write_bytes(b"png")
                (assets / f"{number:02d}.mp4").write_bytes(b"mp4")
            payload = {"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"An evidence-led story useful to every age.","wonder_hook":"Could this test work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"assets-ready-for-assembly","scenes":[{"n":number,"beat":"hook","visual":"AION explores.","narration":"One.","image":f"assets/content-library/aion-stories/episode/{number:02d}.png","motion_path":f"assets/content-library/aion-stories/episode/{number:02d}.mp4"} for number in (1, 2, 3)]}
            (episode_dir / "episode.json").write_text(json.dumps(payload), encoding="utf-8")
            def renderer(_, __, output, **kwargs):
                self.assertEqual(3, len(kwargs["motion_paths"]))
                Path(output).parent.mkdir(parents=True, exist_ok=True); Path(output).write_bytes(b"mp4")
            with mock.patch("tools.assemble_creator_episode.VideoQualityGate.assess", return_value={"eligible": True}):
                result = assemble_once(root, renderer=renderer)
            self.assertEqual("episode-rendered-for-quality", result["stage"])

    def test_does_not_claim_a_video_when_no_episode_is_ready(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual("no-asset-complete-episode", assemble_once(root)["stage"])

    def test_refuses_static_assembly_until_automatic_motion_is_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            assets = root / "assets" / "content-library" / "aion-stories" / "episode"; assets.mkdir(parents=True)
            for number in (1, 2, 3): (assets / f"{number:02d}.png").write_bytes(b"png")
            payload = {"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"An evidence-led story useful to every age.","wonder_hook":"Could this test work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"assets-ready-for-assembly","scenes":[{"n":number,"beat":"hook","visual":"AION explores.","narration":"One.","image":f"assets/content-library/aion-stories/episode/{number:02d}.png"} for number in (1, 2, 3)]}
            (episode_dir / "episode.json").write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual("waiting-for-automatic-motion", assemble_once(root)["stage"])

    def test_restores_a_missing_caption_track_without_re_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            reels = root / "content" / "reels"; reels.mkdir(parents=True)
            (reels / "episode.mp4").write_bytes(b"existing video")
            payload = {
                "id":"episode", "series":"AION Wonders", "title":"A useful test story",
                "status":"production-ready-assets-and-script", "format":"illustrated-narrated-short",
                "scene_seconds":5, "target_duration_seconds":15,
                "audience_promise":"Viewers learn why accessible captions matter to every audience.",
                "wonder_hook":"Could captions save a finished story?", "creative_device":"journey",
                "age_layers":{"children":"Ask.", "family":"Talk.", "deeper":"Test."},
                "science_boundary":"This is a test boundary.",
                "sources":[{"url":"https://one.test"}, {"url":"https://two.test"}],
                "scenes":[
                    {"n":1, "narration":"One.", "visual":"AION explores captions."},
                    {"n":2, "narration":"Two.", "visual":"AION checks timing."},
                    {"n":3, "narration":"Three.", "visual":"AION completes the repair."},
                ],
            }
            (episode_dir / "episode.json").write_text(json.dumps(payload), encoding="utf-8")
            report = backfill_subtitles_once(root)
            self.assertEqual(1, report["count"])
            self.assertTrue((reels / "episode.srt").is_file())
            self.assertEqual(b"existing video", (reels / "episode.mp4").read_bytes())
