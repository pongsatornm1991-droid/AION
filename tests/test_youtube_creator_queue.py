import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from brain.memory import MemoryEngine
from brain.youtube_creator_queue import YouTubeCreatorQueue


class YouTubeCreatorQueueTests(unittest.TestCase):
    def _episode(self, root):
        series = Path(root) / "content" / "creator_series"
        images = Path(root) / "assets" / "images"
        reels = Path(root) / "content" / "reels"
        series.mkdir(parents=True)
        images.mkdir(parents=True)
        reels.mkdir(parents=True)
        for number in range(3):
            (images / f"{number}.png").write_bytes(b"image")
        (series / "episode.json").write_text(__import__("json").dumps({
            "id": "episode", "series": "AION Wonders", "title": "A useful question",
            "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
            "target_duration_seconds": 18, "scene_seconds": 6,
            "audience_promise": "Viewers learn how a careful question can make a mystery easier to explore.",
            "wonder_hook": "Could a small question change how we see the world?", "creative_device": "journey",
            "age_layers": {"children": "Ask why.", "family": "Talk together.", "deeper": "Test a claim."},
            "science_boundary": "This is a story prompt, not scientific proof.",
            "sources": [{"url": "https://example.test/one"}, {"url": "https://example.test/two"}],
            "scenes": [
                {"n": n, "image": f"assets/images/{n}.png", "visual": "AION explores a new place.", "narration": "AION asks a careful question."}
                for n in range(3)
            ],
        }), encoding="utf-8")

    def test_prepares_rendered_episode_without_uploading(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("upload-ready", queue.candidates()[0]["status"])
            report = queue.prepare_once()
            self.assertEqual("prepared-for-review", report["stage"])
            self.assertEqual("awaiting-human-confirmation", report["upload_status"])
            self.assertEqual("already-prepared", queue.candidates()[0]["status"])
            self.assertEqual("no-upload-ready-creator-episode", queue.prepare_once()["stage"])

    def test_publishes_authorized_episode_once_when_project_policy_delegates_it(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("authorized-for-publishing", queue.prepare_once()["stage"])
            self.assertEqual("authorized-for-aion-publish", queue.candidates()[0]["publication_status"])
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}):
                captured = {}
                def uploader(path, title, description):
                    captured["description"] = description
                    return {"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "public"}
                result = queue.publish_once(uploader)
            self.assertEqual("published", result["stage"])
            self.assertIn("#Shorts", captured["description"])
            self.assertEqual("published", queue.candidates()[0]["status"])
            self.assertEqual("no-authorized-creator-episode", queue.publish_once()["stage"])

    def test_migrates_old_confirmation_record_when_policy_is_delegated(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("prepared-for-review", queue.prepare_once()["stage"])
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            migrated = queue.prepare_once()
            self.assertTrue(migrated["migrated"])
            self.assertEqual("authorized-for-aion-publish", migrated["upload_status"])

    def test_video_qa_can_block_an_authorized_upload(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            queue.prepare_once()
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": False, "reasons": ["missing-audio-stream"]}):
                result = queue.publish_once(lambda *_: {"video_id": "should-not-upload"})
            self.assertEqual("quality-review-required", result["stage"])
            self.assertIn("video-qa:missing-audio-stream", result["reasons"])
            gate = queue.candidates()[0]["quality_gate"]
            self.assertFalse(gate["eligible"])
            self.assertIn("video-qa:missing-audio-stream", gate["reasons"])

    def test_vertical_feature_uses_shorts_tag_after_passing_qa(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            queue.prepare_once()
            qa = {"eligible": True, "reasons": [], "technical": {"width": 1080, "height": 1920, "duration_seconds": 120}}
            captured = {}
            with patch("brain.video_quality.VideoQualityGate.assess", return_value=qa):
                queue.publish_once(lambda _path, _title, description: captured.update(description=description) or {"video_id": "abc"})
            self.assertIn("#Shorts", captured["description"])

    def test_records_an_actionable_error_when_uploader_exception_has_no_message(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            queue.prepare_once()
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}):
                result = queue.publish_once(lambda *_: (_ for _ in ()).throw(RuntimeError()))
            self.assertEqual("upload-failed", result["stage"])
            self.assertEqual("RuntimeError", result["error"])

    def test_audits_published_episode_without_uploading_again(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            queue.prepare_once()
            entry = memory.all(queue.CATEGORY)[0]
            payload = __import__("json").loads(entry["content"])
            payload.update({"upload_status": "published", "youtube": {"video_id": "abc"}})
            memory.update(queue.CATEGORY, entry["id"], content=__import__("json").dumps(payload))
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}):
                result = queue.audit_existing()
            self.assertEqual("video-qa-recorded", result["stage"])
            self.assertEqual(True, queue.candidates()[0]["video_qa"]["eligible"])

    def test_short_filter_never_selects_a_long_form_episode(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            episode = Path(root) / "content" / "creator_series" / "episode.json"
            payload = __import__("json").loads(episode.read_text(encoding="utf-8"))
            payload["format"] = "long-form-illustrated"
            payload["scenes"] = payload["scenes"] * 8
            for index, scene in enumerate(payload["scenes"]): scene["n"] = index + 1
            payload["target_duration_seconds"] = len(payload["scenes"]) * payload["scene_seconds"]
            episode.write_text(__import__("json").dumps(payload), encoding="utf-8")
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            self.assertEqual("no-upload-ready-creator-episode", queue.prepare_once("short")["stage"])
            self.assertEqual("prepared-for-review", queue.prepare_once("long-form")["stage"])
