import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.memory import MemoryEngine
from brain.story_episode_stager import StoryEpisodeStager
from brain.creator_scene_production import CreatorSceneProduction


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

    def test_clean_never_cuts_a_word_in_half(self):
        # Regression for 2026-09-22: a bare [:limit] slice once produced
        # narration reading "...deep reddish pu" -- the source text ran
        # past the limit right in the middle of "purple".
        long_text = "deep reddish " + "purple " * 100
        cleaned = StoryEpisodeStager._clean(long_text, limit=20)
        self.assertFalse(cleaned.endswith("pu"))
        for word in cleaned.split():
            self.assertIn(word, long_text.split())

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
