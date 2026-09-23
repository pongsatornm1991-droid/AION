import tempfile
import unittest
from pathlib import Path

from brain.creator_scene_production import CreatorSceneProduction
from brain.visual_story_policy import VisualStoryPolicy


class CreatorSceneProductionTests(unittest.TestCase):
    def test_storyboard_can_name_future_asset_paths_before_generation(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            (episode_dir / "episode.json").write_text('''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")
            result = CreatorSceneProduction(root, lambda _, destination: (Path(destination).write_bytes(b"png") or True)).produce_once(limit=1)
            self.assertEqual([1], result["produced"])

    def test_background_scene_does_not_force_aion_into_frame(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A Roman baker pulls bread from a busy oven."}
        )
        self.assertIn("Do not include AION in this scene", prompt)
        self.assertIn("never make AION the hero", prompt)
        self.assertIn("story-specific chosen presence", prompt)

    def test_animated_documentary_episode_uses_the_approved_original_style(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-animated-documentary-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A Roman baker pulls bread from a busy oven."}
        )
        self.assertIn("premium 2D animated documentary illustration", prompt)
        self.assertIn("Do not imitate any named artist", prompt)

    def test_neon_graphic_science_blends_a_restrained_magenta_or_yellow_accent(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-graphic-science-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A Venus flytrap closes on a second touch."}
        )
        self.assertIn("AION Neon Graphic Science", prompt)
        # The base functional colour roles stay in place...
        self.assertIn("cyan is reserved only for AION's tiny", prompt)
        # ...and a magenta/yellow neon accent is blended in, restrained and
        # scoped to one element, never replacing the base roles.
        self.assertIn("hot-magenta or cyber-yellow", prompt)
        self.assertIn("blended into this palette rather than replacing it", prompt)
        self.assertIn("never as general scene lighting", prompt)

    def test_neon_vector_shorts_is_bold_flat_and_replaces_the_restrained_palette(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-vector-shorts-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A bioluminescent jellyfish pulses in the deep sea."}
        )
        self.assertIn("AION Neon Vector Shorts", prompt)
        self.assertIn("flat 2D vector", prompt)
        self.assertIn("No thick black ink outlines", prompt)
        self.assertIn("electric pink/magenta", prompt)
        self.assertIn("REPLACES the channel's usual restrained palette", prompt)
        self.assertIn("cyan", prompt)
        self.assertIn("never a full body colour", prompt)
        self.assertIn("never imitate a named artist, studio, channel, mascot or franchise", prompt)

    def test_neon_vector_shorts_cover_matches_the_scene_style_instead_of_warm_3d(self):
        episode = {
            "format": "illustrated-narrated-short",
            "wonder_hook": "Why do jellyfish glow?",
            "scenes": [{"visual": "A jellyfish glows in dark water."}],
            "visual_style": {"id": "aion-neon-vector-shorts-v1"},
        }
        cover_prompt = CreatorSceneProduction()._cover_prompt(episode)
        self.assertIn("AION Neon Vector Shorts", cover_prompt)
        self.assertNotIn("warm 3D educational storytelling with rounded appealing forms", cover_prompt)
        self.assertNotIn("do not use grey wash, neon clutter", cover_prompt)

    def test_neon_diorama_3d_is_glossy_and_replaces_the_restrained_palette(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A bioluminescent jellyfish pulses in the deep sea."}
        )
        self.assertIn("AION Neon Diorama 3D", prompt)
        self.assertIn("cinematic 3D-rendered miniature-world", prompt)
        self.assertIn("believable wet metal, stone, glass, water, soil, weather and light", prompt)
        self.assertIn("shallow depth of field", prompt)
        self.assertIn("electric pink/magenta", prompt)
        self.assertIn("REPLACES the channel's usual restrained palette", prompt)
        self.assertIn("cyan", prompt)
        self.assertIn("never a full body colour", prompt)
        self.assertIn("never imitate a named artist, studio, channel, mascot or franchise", prompt)

    def test_neon_diorama_3d_cover_matches_the_scene_style_instead_of_warm_3d(self):
        episode = {
            "format": "illustrated-narrated-short",
            "wonder_hook": "Why do jellyfish glow?",
            "scenes": [{"visual": "A jellyfish glows in dark water."}],
            "visual_style": {"id": "aion-neon-diorama-3d-v1"},
        }
        cover_prompt = CreatorSceneProduction()._cover_prompt(episode)
        self.assertIn("AION Neon Diorama 3D", cover_prompt)
        self.assertNotIn("warm 3D educational storytelling with rounded appealing forms", cover_prompt)
        self.assertNotIn("do not use grey wash, neon clutter", cover_prompt)

    def test_thoughtscape_direction_is_specific_to_the_story_without_copying_a_style(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-thoughtscape-director-v1", "director": {
                       "world": "ocean", "mood": "luminous marine curiosity",
                       "palette_and_material": "glass light", "rendering_rule": "Original work only; never imitate a named studio."}}}
        prompt = CreatorSceneProduction()._prompt(episode, {"visual": "An octopus moves through coral."})
        self.assertIn("AION Thoughtscape direction", prompt)
        self.assertIn("World: ocean", prompt)
        self.assertIn("never imitate a named studio", prompt)

    def test_creates_bounded_fresh_assets_and_updates_storyboard(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            (episode_dir / "episode.json").write_text('''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")
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
            original = '''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}'''
            source.write_text(original, encoding="utf-8")
            result = CreatorSceneProduction(root, lambda *_: False).produce_once(limit=1)
            self.assertEqual("scene-generation-unavailable", result["stage"])
            self.assertEqual(original, source.read_text(encoding="utf-8"))

    def test_completes_an_episode_in_multiple_batches_without_daily_wait(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            source = episode_dir / "episode.json"
            source.write_text('''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")

            def generator(_, destination):
                from PIL import Image
                size = (1280, 720) if str(destination).endswith("-cover.png") else (100, 100)
                Image.new("RGB", size, color=(40, 120, 180)).save(destination)
                return True

            result = CreatorSceneProduction(root, generator).produce_episode(batch_size=2, max_scenes=25)
            updated = source.read_text(encoding="utf-8")
            self.assertEqual("episode-assets-complete", result["stage"])
            self.assertEqual([1, 2, 3], result["produced"])
            self.assertEqual(2, result["batches"])
            self.assertTrue((root / "content" / "reels" / "episode-cover.png").is_file())
            self.assertIn('"status": "assets-ready-for-assembly"', updated)

    def test_already_complete_short_with_a_valid_vertical_cover_is_not_reselected(self):
        """Regression: an already-published Short with all scenes rendered and a
        real vertical 9:16 cover must be recognised as complete, never picked
        as a production candidate again. Before this fix, _cover_exists()
        only accepted a landscape 16:9 cover, so a finished Short's correct
        vertical cover looked "missing" forever -- the episode kept getting
        re-selected every scheduled shift, produced nothing (all scenes
        already had images), and starved every other episode queued behind
        it out of that shift (this is exactly what happened to a real
        already-published episode in production).
        """
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            reels_dir = root / "content" / "reels"; reels_dir.mkdir(parents=True)
            source = episode_dir / "episode.json"
            source.write_text('''{"id":"episode","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"production-ready-assets-and-script","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One.","image":"assets/content-library/aion-stories/episode/01-hook.png"},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two.","image":"assets/content-library/aion-stories/episode/02-reveal.png"},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three.","image":"assets/content-library/aion-stories/episode/03-end.png"}]}''', encoding="utf-8")
            from PIL import Image
            Image.new("RGB", (1080, 1920), color=(20, 30, 40)).save(reels_dir / "episode-cover.png")
            scenes_dir = root / "assets" / "content-library" / "aion-stories" / "episode"; scenes_dir.mkdir(parents=True)
            for name in ("01-hook.png", "02-reveal.png", "03-end.png"):
                (scenes_dir / name).write_bytes(b"png")

            def generator(*_):
                raise AssertionError("a real generator call means the fix did not stop re-selection")

            production = CreatorSceneProduction(root, generator)
            self.assertIsNone(production._episode())
            # With no eligible candidate left, produce_once must report there
            # is nothing to do rather than ever calling the generator again.
            result = production.produce_once(limit=5)
            self.assertEqual("no-subject-first-storyboard-ready", result["stage"])
