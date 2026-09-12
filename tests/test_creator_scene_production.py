import tempfile
import unittest
from pathlib import Path

from brain.creator_scene_production import CreatorSceneProduction
from brain.visual_story_policy import VisualStoryPolicy


class CreatorSceneProductionTests(unittest.TestCase):
    def test_creates_bounded_fresh_assets_and_updates_storyboard(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            (episode_dir / "episode.json").write_text('''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.28},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")
            def generator(prompt, destination):
                Path(destination).write_bytes(b"png")
                return "Visual focus" in prompt
            result = CreatorSceneProduction(root, generator).produce_once(limit=2)
            self.assertEqual([1, 2], result["produced"])
            self.assertTrue((root / "assets" / "content-library" / "aion-stories" / "episode" / "01-hook.png").is_file())

    def test_unavailable_generator_does_not_rewrite_storyboard(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            source = episode_dir / "episode.json"
            original = '''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.28},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}'''
            source.write_text(original, encoding="utf-8")
            result = CreatorSceneProduction(root, lambda *_: False).produce_once(limit=1)
            self.assertEqual("scene-generation-unavailable", result["stage"])
            self.assertEqual(original, source.read_text(encoding="utf-8"))
