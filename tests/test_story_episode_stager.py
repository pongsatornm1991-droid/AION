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
