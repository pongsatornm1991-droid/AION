import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.memory import MemoryEngine
from brain.story_episode_stager import StoryEpisodeStager
from brain.creator_scene_production import CreatorSceneProduction


class FakeProvider:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.response


class RewriteSceneNarrationsTests(unittest.TestCase):
    SCENES = [
        {"n": 1, "beat": "hook", "narration": "Chromatophores let an octopus change color in under one second."},
        {"n": 2, "beat": "question", "narration": "We will follow what was actually observed."},
        {"n": 4, "beat": "evidence-one-a", "narration": "Muscles stretch each pigment sac to reveal or hide its color."},
    ]

    def test_no_provider_is_a_bounded_fallback_and_leaves_narration_untouched(self):
        stager = StoryEpisodeStager(memory=None, root=".", provider=None)
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual("bounded-fallback", meta["origin"])
        self.assertEqual("provider-unavailable", meta["reason"])
        self.assertEqual(self.SCENES[0]["narration"], scenes[0]["narration"])

    def test_applies_a_safe_rewrite_that_preserves_key_facts(self):
        response = json.dumps({
            "1": "Meet the octopus: it can flip its whole color scheme in under a second using Chromatophores!",
            "4": "Here's the trick -- Muscles stretch each pigment sac open to flash color, or hide it.",
        })
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(response=response))
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual("ai-rewrite", meta["origin"])
        self.assertEqual([1, 4], meta["rewritten_scenes"])
        self.assertIn("Chromatophores", scenes[0]["narration"])
        self.assertNotEqual(self.SCENES[0]["narration"], scenes[0]["narration"])
        # The untargeted "question" beat is never touched.
        self.assertEqual(self.SCENES[1]["narration"], scenes[1]["narration"])

    def test_falls_back_to_the_original_line_when_a_candidate_claims_consciousness(self):
        response = json.dumps({
            "1": "I feel so alive watching this octopus change color!",
            "4": "Muscles stretch each pigment sac to reveal or hide its color, live on screen.",
        })
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(response=response))
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual(self.SCENES[0]["narration"], scenes[0]["narration"])
        self.assertIn({"n": 1, "reason": "claim-safety"}, meta["skipped"])
        self.assertIn(4, meta["rewritten_scenes"])

    def test_falls_back_to_the_original_line_when_a_candidate_drifts_from_the_facts(self):
        response = json.dumps({
            "1": "This amazing creature can do all sorts of incredible things you would never expect!",
            "4": "Muscles stretch each pigment sac to reveal or hide its color.",
        })
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(response=response))
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual(self.SCENES[0]["narration"], scenes[0]["narration"])
        self.assertIn({"n": 1, "reason": "fact-drift"}, meta["skipped"])

    def test_a_provider_failure_is_a_bounded_fallback_not_a_crash(self):
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(exc=RuntimeError("provider down")))
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual("bounded-fallback", meta["origin"])
        self.assertEqual("provider-error:RuntimeError", meta["reason"])
        self.assertEqual(self.SCENES[0]["narration"], scenes[0]["narration"])

    def test_a_non_object_json_response_is_a_bounded_fallback_not_a_crash(self):
        # Regression: valid JSON that isn't an object (e.g. the model
        # returns a bare array) used to raise an uncaught AttributeError
        # on rewritten_by_number.get(...), crashing staging entirely --
        # defeating this method's own documented "never blocks staging"
        # guarantee.
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(response='["line one", "line two"]'))
        scenes, meta = stager._rewrite_scene_narrations([dict(s) for s in self.SCENES], "octopus color change")
        self.assertEqual("bounded-fallback", meta["origin"])
        self.assertEqual("provider-error:ValueError", meta["reason"])
        self.assertEqual(self.SCENES[0]["narration"], scenes[0]["narration"])

    def test_no_rewritable_beats_is_a_bounded_fallback(self):
        stager = StoryEpisodeStager(memory=None, root=".", provider=FakeProvider(response="{}"))
        scenes, meta = stager._rewrite_scene_narrations(
            [{"n": 1, "beat": "question", "narration": "We will follow what was actually observed."}], "topic",
        )
        self.assertEqual("bounded-fallback", meta["origin"])
        self.assertEqual("no-rewritable-beats", meta["reason"])


class StoryEpisodeStagerTests(unittest.TestCase):
    def test_stages_one_traceable_subject_first_short(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-123",
                "topic": "How did an ancient ice house work?",
                "working_title": "AION Wonders: Desert Ice",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one", "observation": "Ice was stored below ground."},
                    {"title": "Source two", "url": "https://example.test/two", "observation": "Wind and shade reduced heat."},
                ],
                "unknown_facts": "The exact temperature varied by season.",
            }), memory_type="decision", source="test", importance=4)
            report = StoryEpisodeStager(memory, root).stage_once()
            self.assertEqual("storyboard-staged", report["stage"])
            episode = CreatorSeriesRegistry(root).episodes()[0]
            self.assertEqual("storyboard-ready-needs-assets", episode["status"])
            self.assertEqual(12, len(episode["scenes"]))
            self.assertEqual(5, episode["scene_seconds"])
            self.assertEqual(60, episode["target_duration_seconds"])
            self.assertEqual("bounded-fallback", episode["visual_style"]["aion_deliberation"]["origin"])
            self.assertEqual("no-story-ready-handoff", StoryEpisodeStager(memory, root).stage_once()["stage"])
            self.assertEqual("bounded-fallback", episode["narration_style"]["origin"])

    def test_stages_with_an_ai_narration_rewrite_when_a_provider_is_configured(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-rewrite",
                "topic": "How did an ancient ice house work?",
                "working_title": "AION Wonders: Desert Ice",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one", "observation": "Ice was stored below ground in a Yakhchal."},
                    {"title": "Source two", "url": "https://example.test/two", "observation": "Wind and shade reduced heat near the structure."},
                ],
                "unknown_facts": "The exact temperature varied by season.",
            }), memory_type="decision", source="test", importance=4)

            class RewriteProvider:
                def generate(self, prompt):
                    payload = json.loads(prompt.splitlines()[-1])
                    return json.dumps({n: f"Picture this: {item['original']}" for n, item in payload.items()})

            report = StoryEpisodeStager(memory, root, provider=RewriteProvider()).stage_once()
            self.assertEqual("storyboard-staged", report["stage"])
            episode = CreatorSeriesRegistry(root).episodes()[0]
            self.assertEqual("ai-rewrite", episode["narration_style"]["origin"])
            hook = episode["scenes"][0]
            self.assertTrue(hook["narration"].startswith("Picture this:"))

    def test_clean_never_cuts_a_word_in_half(self):
        # Regression for 2026-09-22: a bare [:limit] slice once produced
        # narration reading "...deep reddish pu" -- the source text ran
        # past the limit right in the middle of "purple".
        long_text = "deep reddish " + "purple " * 100
        cleaned = StoryEpisodeStager._clean(long_text, limit=20)
        self.assertFalse(cleaned.endswith("pu"))
        for word in cleaned.split():
            self.assertIn(word, long_text.split())

    def test_clean_strips_leading_and_mid_text_bullet_markup(self):
        # Regression for 2026-09-27 (owner: narration should sound like told
        # content, not a research memo): a source observation copy-pasted
        # from an encyclopedia carried its own "- " list markers straight
        # into spoken narration.
        text = "- The article describes maps. - It notes satellite views."
        cleaned = StoryEpisodeStager._clean(text)
        self.assertEqual("The article describes maps. It notes satellite views.", cleaned)

    def test_clean_never_touches_a_real_hyphen_inside_a_word(self):
        cleaned = StoryEpisodeStager._clean("Real-time traffic layers update continuously.")
        self.assertIn("Real-time", cleaned)

    def test_evidence_parts_prefer_a_real_sentence_end_over_a_blind_word_count_cut(self):
        # Regression for 2026-09-27: a blind 12-word cut landed mid-clause
        # ("...satellite imagery, aerial.") instead of a real sentence end
        # that falls within the natural window around words_per_part.
        observation = (
            "Google Maps presents several distinct map representations to explore. "
            "It moved from a flat 2D projection to a 3D globe view in 2018."
        )
        parts = StoryEpisodeStager._evidence_parts(observation, part_count=2, words_per_part=12)
        self.assertTrue(parts[0].endswith("explore."))

    def test_evidence_parts_prefer_a_comma_over_a_mid_word_cut_when_no_sentence_end_is_near(self):
        # The bug this whole change targets: the original code would cut
        # this exact sentence to "...satellite imagery, aerial." -- stopping
        # mid-list on a word that isn't even a natural pause.
        observation = (
            "The article describes that Google Maps presents multiple map representations, "
            "satellite imagery, aerial photos, street maps, and real-time traffic layers, "
            "and allows users to switch among them."
        )
        parts = StoryEpisodeStager._evidence_parts(observation, part_count=2, words_per_part=12)
        self.assertNotEqual("aerial", parts[0].rstrip(".").split()[-1])
        self.assertTrue(parts[0].endswith("."))

    def test_evidence_parts_use_an_ellipsis_not_a_fabricated_period_when_cut_is_blind(self):
        # A single run-on sentence with no comma or sentence end anywhere
        # near the window must not be presented as if it were complete.
        observation = " ".join(f"word{i}" for i in range(40)) + "."
        parts = StoryEpisodeStager._evidence_parts(observation, part_count=2, words_per_part=12)
        self.assertTrue(parts[0].endswith("…"))
        self.assertNotIn(".", parts[0])

    def test_evidence_parts_never_adds_a_spurious_ellipsis_after_an_already_complete_short_sentence(self):
        # Regression: an observation short enough that neither boundary
        # search ever reaches min_end (so the blind word-count cut always
        # fires) still ended in a real period -- the old code appended "…"
        # after it anyway, producing "Ice was stored below ground.…".
        observation = "Ice was stored below ground."
        parts = StoryEpisodeStager._evidence_parts(observation, part_count=2, words_per_part=12)
        self.assertEqual(["Ice was stored below ground."], parts)

    def test_connection_beat_states_real_evidence_instead_of_generic_filler(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-mechanism",
                "topic": "How can an octopus change color so quickly?",
                "working_title": "AION Wonders: Octopus Color",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one",
                     "observation": "Chromatophores are pigment sacs controlled directly by nerves and muscles."},
                    {"title": "Source two", "url": "https://example.test/two",
                     "observation": "Muscles stretch each sac to reveal or hide its pigment within milliseconds."},
                ],
                "unknown_facts": "The exact neural pathway is still being mapped.",
            }), memory_type="decision", source="test", importance=4)
            StoryEpisodeStager(memory, root).stage_once()
            episode = CreatorSeriesRegistry(root).episodes()[0]
            connection = next(scene for scene in episode["scenes"] if scene["beat"] == "connection")
            self.assertNotEqual(
                f"Together, these two observations give us a clearer picture of {episode['wonder_hook']}.",
                connection["narration"],
            )
            self.assertIn("Chromatophores", connection["narration"])
            self.assertIn("Muscles", connection["narration"])

    def test_hook_leads_with_a_sourced_fact_instead_of_announcing_the_show(self):
        # Regression for 2026-09-22 (owner: focus on Shorts, aim for
        # kurzgesagt-calibre memorability): every episode used to open on
        # the identical "Today we are asking: {topic}" preamble.
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-hook",
                "topic": "How can an octopus change color so quickly?",
                "working_title": "AION Wonders: Octopus Color",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one",
                     "observation": "Chromatophores let some octopuses shift color in under one second."},
                    {"title": "Source two", "url": "https://example.test/two",
                     "observation": "Muscles stretch each pigment sac to reveal or hide its color."},
                ],
                "unknown_facts": "The exact neural pathway is still being mapped.",
            }), memory_type="decision", source="test", importance=4)
            StoryEpisodeStager(memory, root).stage_once()
            episode = CreatorSeriesRegistry(root).episodes()[0]
            hook = episode["scenes"][0]
            self.assertNotIn("Today we are asking", hook["narration"])
            self.assertIn("Chromatophores", hook["narration"])
            self.assertIn(episode["wonder_hook"], hook["narration"])

    def test_ending_closes_on_the_topic_instead_of_a_generic_sign_off(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-ending",
                "topic": "How can an octopus change color so quickly?",
                "working_title": "AION Wonders: Octopus Color",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one", "observation": "Chromatophores let color shift fast."},
                    {"title": "Source two", "url": "https://example.test/two", "observation": "Muscles reveal or hide each pigment sac."},
                ],
                "unknown_facts": "The exact neural pathway is still being mapped.",
            }), memory_type="decision", source="test", importance=4)
            StoryEpisodeStager(memory, root).stage_once()
            episode = CreatorSeriesRegistry(root).episodes()[0]
            ending = episode["scenes"][-1]
            self.assertNotEqual("Keep asking better questions, and check the evidence with me.", ending["narration"])
            self.assertFalse(ending["narration"].strip().endswith("?"))
            self.assertIn(episode["wonder_hook"], ending["narration"])

    def test_stages_a_bounded_batch_of_storyboards_instead_of_stopping_at_one(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            for index in range(2):
                memory.remember("creator_research_handoffs", json.dumps({
                    "status": "story-ready", "root_question_id": f"question-batch-{index}",
                    "topic": f"How did an ancient ice house work, case {index}?",
                    "working_title": f"AION Wonders: Desert Ice {index}",
                    "sources": [
                        {"title": "Source one", "url": f"https://example.test/{index}-one", "observation": "Ice was stored below ground."},
                        {"title": "Source two", "url": f"https://example.test/{index}-two", "observation": "Wind and shade reduced heat."},
                    ],
                    "unknown_facts": "The exact temperature varied by season.",
                }), memory_type="decision", source="test", importance=4)
            stager = StoryEpisodeStager(memory, root)
            result = stager.stage_batch(limit=5)
            self.assertEqual("story-batch-complete", result["stage"])
            self.assertEqual(2, len(result["staged_episode_ids"]))
            self.assertEqual(2, len(CreatorSeriesRegistry(root).episodes()))
            self.assertEqual("no-story-ready-handoff", stager.stage_batch(limit=5)["stage"])

    def test_studio_shift_stops_after_its_episode_limit(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            series = root / "content" / "creator_series"
            series.mkdir(parents=True)
            for index in range(2):
                (series / f"episode-{index}.json").write_text(json.dumps({
                    "id": f"episode-{index}", "series": "AION Wonders", "title": "A useful question",
                    "status": "storyboard-ready-needs-assets", "format": "illustrated-narrated-short",
                    "target_duration_seconds": 60, "scene_seconds": 5, "pacing_policy": "fast-cut-subject-first-v1",
                    "audience_promise": "A viewer learns to compare evidence before accepting a surprising claim.",
                    "wonder_hook": "Could a careful question reveal something unexpected?", "creative_device": "mystery-reveal",
                    "age_layers": {"children": "Notice clues.", "family": "Compare ideas.", "deeper": "Test evidence."},
                    "sources": [{"url": "https://example.test/one"}, {"url": "https://example.test/two"}],
                    "uncertainty_boundary": "The evidence does not settle every detail.",
                    "visual_direction": {"focus": "subject-first", "aion_role": "contextual-guide", "aion_frame_share_max": 0.2},
                    "visual_identity": {"version": "aion-stylized-guide-real-world-v1"},
                    "scenes": [{"n": number, "visual": "AION appears briefly while the subject dominates the frame.", "narration": "AION asks a careful question."} for number in range(1, 13)],
                }), encoding="utf-8")
            made = []
            def generator(_prompt, destination):
                from PIL import Image
                size = (1280, 720) if str(destination).endswith("-cover.png") else (100, 100)
                Image.new("RGB", size, color=(40, 120, 180)).save(destination)
                made.append(destination)
                return True
            report = CreatorSceneProduction(root, generator=generator).produce_ready_episodes(episode_limit=2, batch_size=3)
            self.assertEqual("studio-shift-complete", report["stage"])
            self.assertEqual(2, len(report["completed_episode_ids"]))
            # Twelve scenes plus one standalone custom YouTube cover per episode.
            self.assertEqual(26, len(made))

    def test_stages_a_distinct_two_minute_primary_episode_from_the_same_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            memory = MemoryEngine(root / "memory")
            memory.remember("creator_research_handoffs", json.dumps({
                "status": "story-ready", "root_question_id": "question-long",
                "topic": "How did an ancient ice house work?",
                "sources": [
                    {"title": "Source one", "url": "https://example.test/one", "observation": "Ice was stored below ground where shade and thick earth slowed heat transfer during the day."},
                    {"title": "Source two", "url": "https://example.test/two", "observation": "Cold clear nights and carefully directed water could create thin ice layers before storage."},
                ],
                "unknown_facts": "The exact temperature varied by season.",
            }), memory_type="decision", source="test", importance=4)
            report = StoryEpisodeStager(memory, root).stage_once("long-form")
            self.assertEqual("storyboard-staged", report["stage"])
            episode = CreatorSeriesRegistry(root).episodes()[0]
            self.assertEqual("long-form-illustrated", episode["format"])
            self.assertEqual(24, len(episode["scenes"]))
            self.assertEqual(120, episode["target_duration_seconds"])
