import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_episode_crosspost import CreatorEpisodeCrosspost
from brain.memory import MemoryEngine


class CreatorEpisodeCrosspostTests(unittest.TestCase):
    def test_crossposts_only_the_named_quality_gated_creator_short_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content/creator_series").mkdir(parents=True)
            (root / "content/reels").mkdir(parents=True)
            episode = {
                "id": "fresh-short", "series": "AION Wonders", "title": "Fresh short",
                "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
                "target_duration_seconds": 60, "scene_seconds": 5, "pacing_policy": "fast-cut-subject-first-v1",
                "audience_promise": "A clear answer helps viewers understand one surprising scientific idea.",
                "wonder_hook": "Why does this surprising thing happen?", "creative_device": "mystery-reveal",
                "age_layers": {"children": "Notice clues.", "family": "Compare clues.", "deeper": "Check evidence."},
                "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                "uncertainty_boundary": "The sources do not answer every detail.",
                "scenes": [{"n": n, "visual": "AION observes the subject.", "narration": "A useful clue."} for n in range(1, 13)],
            }
            (root / "content/creator_series/fresh-short.json").write_text(json.dumps(episode), encoding="utf-8")
            # The unit test replaces the expensive binary inspection with a
            # tiny valid placeholder by patching the gate's result below.
            (root / "content/reels/fresh-short.mp4").write_bytes(b"x")
            memory = MemoryEngine(root / "memory")
            crosspost = CreatorEpisodeCrosspost(memory, root)
            from unittest.mock import patch
            with patch("brain.creator_episode_crosspost.VideoQualityGate.assess", return_value={"eligible": True}), \
                 patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"}, clear=False):
                report = crosspost.publish_once("fresh-short", lambda *_args, **_kwargs: {"id": "ig"}, lambda *_args, **_kwargs: {"id": "fb"})
                self.assertEqual("published", report["stage"])
                second = crosspost.publish_once("fresh-short", lambda *_args, **_kwargs: self.fail("duplicate IG"), lambda *_args, **_kwargs: self.fail("duplicate FB"))
                self.assertEqual("published", second["stage"])

    def test_latest_publish_only_selects_a_public_youtube_short(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content/creator_series").mkdir(parents=True)
            (root / "content/reels").mkdir(parents=True)
            episode = {
                "id": "latest-short", "series": "AION Wonders", "title": "Latest short",
                "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
                "target_duration_seconds": 60, "scene_seconds": 5, "pacing_policy": "fast-cut-subject-first-v1",
                "audience_promise": "A clear answer helps viewers understand one surprising scientific idea.",
                "wonder_hook": "Why does this surprising thing happen?", "creative_device": "mystery-reveal",
                "age_layers": {"children": "Notice clues.", "family": "Compare clues.", "deeper": "Check evidence."},
                "sources": [{"url": "https://one.test"}, {"url": "https://two.test"}],
                "uncertainty_boundary": "The sources do not answer every detail.",
                "scenes": [{"n": n, "visual": "AION observes the subject.", "narration": "A useful clue."} for n in range(1, 13)],
            }
            (root / "content/creator_series/latest-short.json").write_text(json.dumps(episode), encoding="utf-8")
            (root / "content/reels/latest-short.mp4").write_bytes(b"x")
            memory = MemoryEngine(root / "memory")
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "latest-short", "content_kind": "short",
                "youtube": {"video_id": "yt", "privacy_status": "public"},
            }), "action")
            crosspost = CreatorEpisodeCrosspost(memory, root)
            from unittest.mock import patch
            with patch("brain.creator_episode_crosspost.VideoQualityGate.assess", return_value={"eligible": True}), \
                 patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"}, clear=False):
                report = crosspost.publish_latest_once(lambda *_a, **_k: {"id": "ig"}, lambda *_a, **_k: {"id": "fb"})
            self.assertEqual("published", report["stage"])

    def test_latest_publish_skips_a_public_but_underlength_legacy_short(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content/creator_series").mkdir(parents=True)
            (root / "content/reels").mkdir(parents=True)
            for episode_id in ("legacy", "fresh"):
                episode = {"id": episode_id, "series": "AION Wonders", "title": episode_id,
                           "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
                           "target_duration_seconds": 60, "scene_seconds": 5, "audience_promise": "A clear answer.",
                           "wonder_hook": "Why?", "creative_device": "mystery-reveal", "age_layers": {},
                           "sources": [], "scenes": [{"n": n, "visual": "subject", "narration": "clue"} for n in range(1, 13)]}
                (root / f"content/creator_series/{episode_id}.json").write_text(json.dumps(episode), encoding="utf-8")
                (root / f"content/reels/{episode_id}.mp4").write_bytes(b"x")
            memory = MemoryEngine(root / "memory")
            for episode_id in ("fresh", "legacy"):
                memory.remember("youtube_creator_queue", json.dumps({"episode_id": episode_id, "content_kind": "short", "youtube": {"video_id": episode_id, "privacy_status": "public"}}), "action")
            crosspost = CreatorEpisodeCrosspost(memory, root)
            from unittest.mock import patch
            def quality(path, _kind): return {"eligible": Path(path).stem == "fresh"}
            with patch("brain.creator_episode_crosspost.VideoQualityGate.assess", side_effect=quality), patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"}, clear=False):
                report = crosspost.publish_latest_once(lambda *_a, **_k: {"id": "ig"}, lambda *_a, **_k: {"id": "fb"})
            self.assertEqual("fresh", report["episode_id"])
