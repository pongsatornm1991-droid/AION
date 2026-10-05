import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.creator_scene_production import CreatorSceneProduction
from brain.visual_story_policy import VisualStoryPolicy


class CreatorSceneProductionTests(unittest.TestCase):
    def test_current_short_preflight_blocks_old_style_before_image_generation(self):
        episode = {
            "format": "illustrated-narrated-short",
            "pacing_policy": VisualStoryPolicy.VERSION,
            "visual_style": {"id": "legacy-style", "approved": False},
            "scenes": [],
        }

        report = CreatorSceneProduction().preflight(episode)

        self.assertFalse(report["eligible"])
        self.assertIn("visual-style-not-channel-signature", report["reasons"])
        self.assertIn("visual-style-not-approved", report["reasons"])

    def test_current_short_stops_after_an_invalid_pilot_scene(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "episode.json"
            source.write_text("{}", encoding="utf-8")
            episode = {
                "id": "episode", "file": "episode.json", "format": "illustrated-narrated-short",
                "pacing_policy": VisualStoryPolicy.VERSION,
                "visual_style": {"id": VisualStoryPolicy.CHANNEL_VISUAL_STYLE, "approved": True},
                "scenes": [{"n": 1, "beat": "hook", "visual": "A clear mechanism."}],
            }

            def invalid_image(_, destination):
                from PIL import Image
                Image.new("RGB", (100, 100), "navy").save(destination)
                return True

            production = CreatorSceneProduction(root, invalid_image)
            with patch.object(production, "_episode", return_value=episode):
                result = production.produce_once(limit=5)

            self.assertEqual("pilot-scene-rejected", result["stage"])
            self.assertEqual([1], result["failed"])
            self.assertFalse(episode["scenes"][0].get("image"))
            self.assertFalse(result["pilot_scene_qa"]["eligible"])
            archived = episode["scenes"][0]["rejected_assets"][0]["path"]
            self.assertTrue((root / archived).is_file())

    def test_current_short_keeps_valid_scenes_when_only_one_later_scene_fails(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "episode.json"
            source.write_text("{}", encoding="utf-8")
            episode = {
                "id": "episode", "file": "episode.json", "format": "illustrated-narrated-short",
                "pacing_policy": VisualStoryPolicy.VERSION,
                "visual_style": {"id": VisualStoryPolicy.CHANNEL_VISUAL_STYLE, "approved": True},
                "scenes": [
                    {"n": 1, "beat": "hook", "visual": "A clear mechanism."},
                    {"n": 2, "beat": "evidence", "visual": "A second clear mechanism."},
                    {"n": 3, "beat": "takeaway", "visual": "A third clear mechanism."},
                ],
            }

            def mixed_images(_, destination):
                from PIL import Image
                size = (720, 1280) if "01-" in destination else (100, 100)
                Image.new("RGB", size, "navy").save(destination)
                return True

            production = CreatorSceneProduction(root, mixed_images)
            with patch.object(production, "_episode", return_value=episode):
                result = production.produce_once(limit=5)

            self.assertEqual([1], result["produced"])
            self.assertEqual([2], result["failed"])
            self.assertTrue(episode["scenes"][0].get("image"))
            self.assertFalse(episode["scenes"][1].get("image"))
            self.assertFalse(episode["scenes"][2].get("image"))
            self.assertFalse(episode["scenes"][1]["asset_qa"]["eligible"])
            archived = episode["scenes"][1]["rejected_assets"][0]["path"]
            self.assertTrue((root / archived).is_file())

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
        self.assertIn("AION is absent", prompt)

    def test_legacy_aion_wording_cannot_force_aion_into_an_unplanned_scene(self):
        episode = {
            "format": "illustrated-narrated-short",
            "visual_direction": {"aion_presence_beats": ["hook", "takeaway"]},
        }
        prompt = CreatorSceneProduction()._prompt(
            episode, {"beat": "evidence-one-a", "visual": "AION observes a working mechanism."}
        )
        self.assertIn("Do not include AION in this scene", prompt)
        self.assertIn("AION is absent", prompt)
        self.assertNotIn("Wardrobe:", prompt)

    def test_hook_beat_gets_dynamic_framing_within_the_same_diorama_style(self):
        # Owner feedback, 2026-09-27: every scene used identical flat wide
        # framing, reading as static rather than as told content. Only the
        # hook/takeaway beats change; everything else keeps the original
        # wide, calm composition unchanged.
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "hook", "visual": "AION explores a historical place."})
        self.assertIn("dynamic framing with a bold, attention-grabbing angle", prompt)
        self.assertIn("warm 3D diorama material and palette", prompt)
        self.assertIn("never make AION the hero", prompt)

    def test_takeaway_beat_gets_a_more_dramatic_reveal_angle(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "takeaway", "visual": "AION returns to the subject."})
        self.assertIn("more dramatic angle with richer contrast light", prompt)
        self.assertIn("reveal/payoff moment", prompt)

    def test_hook_beat_allows_an_occasional_selfie_style_pov_angle(self):
        # Owner feedback, 2026-09-27, after sharing a Pixar-style selfie
        # reference image: adopt the close first-person POV framing
        # technique, bounded to the hook beat only.
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "hook", "visual": "AION explores a historical place."})
        self.assertIn("first-person point-of-view angle", prompt)
        self.assertIn("candid selfie framing", prompt)

    def test_hook_and_takeaway_beats_allow_a_more_animated_but_still_restrained_reaction(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        hook_prompt = CreatorSceneProduction()._prompt(episode, {"beat": "hook", "visual": "AION explores a historical place."})
        takeaway_prompt = CreatorSceneProduction()._prompt(episode, {"beat": "takeaway", "visual": "AION returns to the subject."})
        for prompt in (hook_prompt, takeaway_prompt):
            self.assertIn("more visibly readable, animated reaction from AION", prompt)
            self.assertIn("never a generic mascot mugging for the camera", prompt)

    def test_an_ordinary_beat_gets_no_selfie_pov_or_heightened_reaction(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "evidence-one-a", "visual": "Show the documented clue."})
        self.assertNotIn("first-person point-of-view angle", prompt)
        self.assertNotIn("animated reaction from AION", prompt)

    def test_an_ordinary_beat_keeps_the_original_wide_calm_composition(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "evidence-one-a", "visual": "Show the documented clue."})
        self.assertIn("wide or medium-wide environmental storytelling", prompt)
        self.assertNotIn("dynamic framing", prompt)
        self.assertNotIn("more dramatic angle", prompt)

    def test_a_scene_with_no_beat_at_all_keeps_the_original_wide_calm_composition(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {}}
        prompt = CreatorSceneProduction()._prompt(episode, {"visual": "A Roman baker pulls bread from a busy oven."})
        self.assertIn("wide or medium-wide environmental storytelling", prompt)

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

    def test_neon_diorama_uses_minimal_composition_without_changing_the_style_id(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"beat": "evidence-one-a", "visual": "A single bubble becomes round."}
        )
        # 2026-10-05: the warm storybook look has its own cinematic camera
        # language; the old "Calm Minimal" quiet-colour-field composition no longer applies.
        self.assertIn("natural cinematic medium-wide view slightly above eye level", prompt)
        self.assertIn("clearest and best-lit element", prompt)
        self.assertNotIn("label callouts", prompt)
        self.assertIn("AION Warm Diorama 3D", prompt)
        self.assertNotIn("Calm Minimal composition layer", prompt)
        self.assertNotIn("quiet colour field", prompt)

    def test_scene_prompt_carries_the_picture_first_reveal_contract(self):
        episode = {
            "format": "illustrated-narrated-short", "visual_direction": {},
            "visual_style": {"id": "aion-neon-diorama-3d-v1"},
            "visual_narrative": {"reveal": {
                "rule": "Show a cutaway that makes the hidden mechanism visible.",
                "placement": "Use the takeaway as the clearest payoff.",
            }},
        }
        prompt = CreatorSceneProduction()._prompt(
            episode, {"beat": "takeaway", "visual": "A pigment sac opens beneath octopus skin."}
        )
        self.assertIn("Picture-first reveal", prompt)
        self.assertIn("cutaway that makes the hidden mechanism visible", prompt)

    def test_neon_diorama_3d_is_glossy_and_replaces_the_restrained_palette(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"visual": "A bioluminescent jellyfish pulses in the deep sea."}
        )
        self.assertIn("AION Warm Diorama 3D", prompt)
        # Owner, 2026-10-05: liked a finished firelit 3D storybook clip -- warm
        # motivated light against violet shadow, dense lived-in set, neon only as
        # small accents, and NOT inside a display case.
        self.assertIn("3D animated-storybook illustration", prompt)
        self.assertIn("lived-in set", prompt)
        self.assertIn("amber and golden firelight or sunlight against deep violet-blue shadows", prompt)
        self.assertIn("neon pink, cyan or violet only as small accents", prompt)
        self.assertIn("never shown inside a display case, glass box", prompt)
        self.assertIn("never a full body colour", prompt)
        self.assertNotIn("Floating holographic label cards", prompt)
        self.assertIn("No text, letters, labels, logos, watermark or UI anywhere.", prompt)

    def test_scene_prompts_allow_label_cards_but_only_with_words_from_the_scene(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        production = CreatorSceneProduction()
        production.LABEL_CARDS = True
        prompt = production._prompt(
            episode, {"beat": "evidence-one-a", "visual": "Magma rises under a thin crust."}
        )
        self.assertIn("Floating holographic label cards", prompt)
        self.assertIn("neon-bordered rounded panels", prompt)
        self.assertIn("taken verbatim from the Scene", prompt)
        self.assertIn("never invented", prompt)
        # The old blanket ban must not contradict the labels in the same prompt.
        self.assertNotIn("No words, captions, logos, watermark, UI, or named-studio imitation.", prompt)
        self.assertIn("Beyond the label cards described in the style", prompt)

    def test_a_guide_beat_keeps_the_label_allowance_consistent(self):
        episode = {"format": "illustrated-narrated-short",
                   "visual_direction": {"aion_presence_beats": ["hook"]},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        production = CreatorSceneProduction()
        production.LABEL_CARDS = True
        prompt = production._prompt(
            episode, {"beat": "hook", "visual": "AION notices magma under a thin crust."}
        )
        self.assertIn("the only text allowed is the floating label cards", prompt)
        self.assertNotIn("No embedded text, logos, watermark", prompt)

    def test_label_cards_are_off_by_default_and_the_no_text_rule_holds(self):
        episode = {"format": "illustrated-narrated-short",
                   "visual_direction": {"aion_presence_beats": ["hook"]},
                   "visual_style": {"id": "aion-neon-diorama-3d-v1"}}
        prompt = CreatorSceneProduction()._prompt(
            episode, {"beat": "hook", "visual": "AION notices magma under a thin crust."}
        )
        self.assertFalse(CreatorSceneProduction.LABEL_CARDS)
        self.assertNotIn("label cards", prompt)
        self.assertIn("No embedded text, logos, watermark", prompt)
        self.assertIn("No words, captions, logos, watermark, UI, or named-studio imitation.", prompt)

    def test_other_styles_keep_their_blanket_no_text_rule(self):
        episode = {"format": "illustrated-narrated-short", "visual_direction": {},
                   "visual_style": {"id": "aion-neon-vector-shorts-v1"}}
        prompt = CreatorSceneProduction()._prompt(episode, {"beat": "evidence-one-a", "visual": "A bubble."})
        self.assertIn("No words, captions, logos, watermark, UI, or named-studio imitation.", prompt)
        self.assertNotIn("Floating holographic label cards", prompt)
        self.assertIn("never imitate a named artist, studio, channel, mascot or franchise", prompt)

    def test_neon_diorama_3d_cover_matches_the_scene_style_instead_of_warm_3d(self):
        episode = {
            "format": "illustrated-narrated-short",
            "wonder_hook": "Why do jellyfish glow?",
            "scenes": [{"visual": "A jellyfish glows in dark water."}],
            "visual_style": {"id": "aion-neon-diorama-3d-v1"},
        }
        cover_prompt = CreatorSceneProduction()._cover_prompt(episode)
        self.assertIn("AION Warm Diorama 3D", cover_prompt)
        self.assertNotIn("warm 3D educational storytelling with rounded appealing forms", cover_prompt)
        self.assertNotIn("do not use grey wash, neon clutter", cover_prompt)
        # A thumbnail carries no label cards: the YouTube title does that job.
        self.assertNotIn("Floating holographic label cards", cover_prompt)
        self.assertIn("No text, letters, labels, logos, watermark or UI anywhere.", cover_prompt)

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

    def test_a_storyboard_flagged_by_the_narration_preflight_is_skipped_for_the_next_one(self):
        """Regression for 2026-10-03: tools/preflight_creator_narration.py now
        flags a storyboard whose narration cannot fit scene timing instead of
        failing the whole batch; scene production must then spend no image
        budget on it and pick the next ready storyboard instead."""
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            base = {"series": "AION Wonders", "title": "Test story", "audience_promise": "A useful evidence-led story for every age.", "wonder_hook": "Could this work?", "creative_device": "journey", "age_layers": {"children": "Ask.", "family": "Talk.", "deeper": "Test."}, "target_duration_seconds": 15, "scene_seconds": 5, "format": "illustrated-narrated-short", "pacing_policy": "fast-cut-subject-first-v1", "visual_direction": {"focus": "subject-first", "aion_role": "contextual-guide", "aion_frame_share_max": 0.20}, "history_boundary": "A boundary.", "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}], "status": "storyboard-ready-needs-assets", "scenes": [{"n": 1, "beat": "hook", "visual": "AION explores a historical place.", "narration": "One."}, {"n": 2, "beat": "reveal", "visual": "AION observes the subject.", "narration": "Two."}, {"n": 3, "beat": "end", "visual": "AION shares a question.", "narration": "Three."}]}
            flagged = {**base, "id": "a-flagged", "narration_preflight": {"eligible": False, "reasons": ["scene-9:narration-exceeds-safe-scene-window"]}}
            (episode_dir / "a-flagged.json").write_text(json.dumps(flagged), encoding="utf-8")
            (episode_dir / "b-ready.json").write_text(json.dumps({**base, "id": "b-ready"}), encoding="utf-8")

            def generator(prompt, destination):
                Path(destination).write_bytes(b"png")
                return "Visual focus" in prompt

            production = CreatorSceneProduction(root, generator)
            result = production.produce_once(limit=1)

            self.assertEqual("b-ready", result["episode_id"])

    def test_one_invalid_episode_does_not_block_a_valid_one_in_the_same_shift(self):
        """Regression for 2026-09-25: CreatorSeriesRegistry.episodes() used to
        raise the moment ANY episode file failed content validation, which
        crashed produce_once() before it could even look for a different,
        genuinely ready episode. Live effect: creator-scene-production.yml
        failed 4 runs in a row and the Shorts buffer stayed at 0/7 because one
        unrelated broken storyboard poisoned every selection attempt.
        """
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            episode_dir = root / "content" / "creator_series"; episode_dir.mkdir(parents=True)
            (episode_dir / "good.json").write_text('''{"id":"good","series":"AION Wonders","title":"Test story","audience_promise":"A useful evidence-led story for every age.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")
            (episode_dir / "bad.json").write_text('''{"id":"bad","series":"AION Wonders","title":"Broken story","audience_promise":"Too short.","wonder_hook":"Could this work?","creative_device":"journey","age_layers":{"children":"Ask.","family":"Talk.","deeper":"Test."},"target_duration_seconds":15,"scene_seconds":5,"format":"illustrated-narrated-short","pacing_policy":"fast-cut-subject-first-v1","visual_direction":{"focus":"subject-first","aion_role":"contextual-guide","aion_frame_share_max":0.20},"history_boundary":"A boundary.","sources":[{"url":"https://one.test"},{"url":"https://two.test"}],"status":"storyboard-ready-needs-assets","scenes":[{"n":1,"beat":"hook","visual":"AION explores a historical place.","narration":"One."},{"n":2,"beat":"reveal","visual":"AION observes the subject.","narration":"Two."},{"n":3,"beat":"end","visual":"AION shares a question.","narration":"Three."}]}''', encoding="utf-8")

            def generator(prompt, destination):
                Path(destination).write_bytes(b"png")
                return "Visual focus" in prompt

            production = CreatorSceneProduction(root, generator)
            result = production.produce_once(limit=2)

            self.assertEqual([1, 2], result["produced"])
            self.assertEqual("good", result["episode_id"])
            self.assertEqual(1, len(production.last_invalid_episodes))
            self.assertEqual("bad", production.last_invalid_episodes[0]["id"])
