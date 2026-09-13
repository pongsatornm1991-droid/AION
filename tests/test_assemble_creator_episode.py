import json
import tempfile
import unittest
from pathlib import Path

from tools.assemble_creator_episode import assemble_once


class AssembleCreatorEpisodeTests(unittest.TestCase):
    def test_assembles_every_scene_then_advances_only_that_episode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            assets = root / "assets" / "content-library" / "aion-stories" / "episode"; assets.mkdir(parents=True)
            for number in (1, 2, 3): (assets / f"{number:02d}.png").write_bytes(b"png")
            payload = {"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"An evidence-led story useful to every age.","wonder_hook":"Could this test work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.28},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"assets-ready-for-assembly","scenes":[{"n":1,"beat":"hook","visual":"AION explores.","narration":"One.","image":"assets/content-library/aion-stories/episode/01.png"},{"n":2,"beat":"reveal","visual":"AION observes.","narration":"Two.","image":"assets/content-library/aion-stories/episode/02.png"},{"n":3,"beat":"end","visual":"AION asks.","narration":"Three.","image":"assets/content-library/aion-stories/episode/03.png"}]}
            source = episode_dir / "episode.json"; source.write_text(json.dumps(payload), encoding="utf-8")
            def renderer(_, __, output, **kwargs):
                self.assertEqual(15, kwargs["duration"]); self.assertEqual(3, len(kwargs["still_paths"]))
                self.assertEqual((1080, 1920), kwargs["frame_size"])
                Path(output).parent.mkdir(parents=True, exist_ok=True); Path(output).write_bytes(b"mp4")
            result = assemble_once(root, renderer=renderer)
            self.assertEqual("episode-rendered-for-quality", result["stage"])
            self.assertTrue((root / result["subtitle_path"]).is_file())
            self.assertIn("00:00:00,000 --> 00:00:05,000", (root / result["subtitle_path"]).read_text(encoding="utf-8"))
            self.assertEqual("production-ready-assets-and-script", json.loads(source.read_text(encoding="utf-8"))["status"])

    def test_does_not_claim_a_video_when_no_episode_is_ready(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual("no-asset-complete-episode", assemble_once(root)["stage"])
