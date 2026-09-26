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
        for number in range(10):
            (images / f"{number}.png").write_bytes(b"image")
        # Every Creator upload now requires a Studio-produced cover.
        from PIL import Image
        Image.new("RGB", (1280, 720), color=(30, 110, 160)).save(reels / "episode-cover.png")
        (series / "episode.json").write_text(__import__("json").dumps({
            "id": "episode", "series": "AION Wonders", "title": "A useful question",
            "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
            "target_duration_seconds": 50, "scene_seconds": 5,
            "visual_style": {"id": "aion-neon-diorama-3d-v1", "approved": True},
            "visual_qa": {"eligible": True, "reasons": []},
            "audience_promise": "Viewers learn how a careful question can make a mystery easier to explore.",
            "wonder_hook": "Could a small question change how we see the world?", "creative_device": "journey",
            "age_layers": {"children": "Ask why.", "family": "Talk together.", "deeper": "Test a claim."},
            "science_boundary": "This is a story prompt, not scientific proof.",
            "sources": [{"url": "https://example.test/one"}, {"url": "https://example.test/two"}],
            "scenes": [
                {"n": n, "image": f"assets/images/{n}.png", "visual": "AION explores a new place.", "narration": "AION asks a careful question."}
                for n in range(10)
            ],
        }), encoding="utf-8")

    def test_prepares_rendered_episode_without_uploading(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("upload-ready", queue.candidates()[0]["status"])
            self.assertEqual("กำลังตรวจ Quality Gate", queue.candidates()[0]["pipeline_stage"]["label"])
            report = queue.prepare_once()
            self.assertEqual("prepared-for-review", report["stage"])
            self.assertEqual("awaiting-human-confirmation", report["upload_status"])
            self.assertEqual(1, report["episode_number"])
            self.assertEqual("EP. 001 — A useful question", report["display_title"])
            self.assertEqual("already-prepared", queue.candidates()[0]["status"])
            self.assertEqual("no-upload-ready-creator-episode", queue.prepare_once()["stage"])

    def test_vertical_short_cover_is_release_eligible(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            from PIL import Image
            Image.new("RGB", (1080, 1920), color=(30, 110, 160)).save(
                root / "content" / "reels" / "episode-cover.png"
            )
            cover = YouTubeCreatorQueue._cover_quality(
                root / "content" / "reels" / "episode-cover.png", "short"
            )
            self.assertTrue(cover["eligible"])
            self.assertFalse(YouTubeCreatorQueue._cover_quality(
                root / "content" / "reels" / "episode-cover.png", "long-form"
            )["eligible"])

    def test_skips_a_legacy_short_instead_of_letting_it_consume_a_release_slot(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            legacy = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            legacy.update({"id": "legacy", "title": "Old draft", "target_duration_seconds": 25})
            legacy["scenes"] = legacy["scenes"][:5]
            (root / "content" / "creator_series" / "legacy.json").write_text(__import__("json").dumps(legacy), encoding="utf-8")
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "legacy.mp4").write_bytes(b"old")
            (root / "content" / "reels" / "legacy-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertFalse(candidates["legacy"]["release_eligible"])
            self.assertEqual("upload-ready", candidates["episode"]["status"])
            self.assertEqual("prepared-for-review", queue.prepare_once()["stage"])
            self.assertEqual("episode", __import__("json").loads(queue.memory.all(queue.CATEGORY)[0]["content"])["episode_id"])

    def test_never_lets_an_unapproved_or_experimental_style_enter_the_release_queue(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            experimental = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            # A style without an explicit approval must never win a release
            # slot, even when it declares urgent priority the way a "special
            # release" would -- this is exactly how an old-style clip won an
            # automatic slot ahead of correctly styled new work.
            experimental.update({
                "id": "experimental", "title": "Old style test",
                "visual_style": {"id": "illustrated-aion-storyboard-v4"},
                "special_release": {"release_priority": "urgent", "reason": "one-off style test"},
            })
            (root / "content" / "creator_series" / "experimental.json").write_text(
                __import__("json").dumps(experimental), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "experimental.mp4").write_bytes(b"old")
            (root / "content" / "reels" / "experimental-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertFalse(candidates["experimental"]["release_eligible"])
            self.assertIn("visual-style-not-approved-for-release", candidates["experimental"]["release_blockers"])
            # The correctly approved episode wins automatic selection instead
            # of the urgent-priority unapproved one.
            report = queue.prepare_once()
            self.assertEqual("prepared-for-review", report["stage"])
            self.assertEqual("episode", report["episode_id"])
            # Explicitly targeting the unapproved episode by id must also
            # refuse it -- style lock is not something --episode-id bypasses.
            self.assertEqual(
                "no-upload-ready-creator-episode",
                queue.prepare_once(episode_id="experimental")["stage"],
            )

    def test_approved_legacy_style_cannot_consume_automatic_daily_slot(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            legacy = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            legacy.update({"id": "legacy-style", "visual_style": {"id": "aion-neon-vector-shorts-v1", "approved": True}})
            (root / "content" / "creator_series" / "legacy-style.json").write_text(__import__("json").dumps(legacy), encoding="utf-8")
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"signature")
            (root / "content" / "reels" / "legacy-style.mp4").write_bytes(b"legacy")
            (root / "content" / "reels" / "legacy-style-cover.png").write_bytes(b"png")
            candidates = {item["episode_id"]: item for item in YouTubeCreatorQueue(MemoryEngine(root / "memory"), root).candidates()}
            self.assertFalse(candidates["legacy-style"]["release_eligible"])
            self.assertIn("visual-style-not-channel-signature", candidates["legacy-style"]["release_blockers"])

    def test_missing_visual_style_field_entirely_also_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            nostyle = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            nostyle.update({"id": "nostyle", "title": "No declared style"})
            del nostyle["visual_style"]
            (root / "content" / "creator_series" / "nostyle.json").write_text(
                __import__("json").dumps(nostyle), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "nostyle.mp4").write_bytes(b"other")
            (root / "content" / "reels" / "nostyle-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertFalse(candidates["nostyle"]["release_eligible"])
            self.assertIn("visual-style-not-approved-for-release", candidates["nostyle"]["release_blockers"])

    def test_unresolved_quality_incident_blocks_release_even_when_status_says_ready(self):
        # Regression for 2026-09-22: an episode was almost re-offered for
        # release because its status string ("quality-blocked-story-and-
        # audio") simply didn't match READY_STATUS -- an accident of
        # spelling, not an enforced gate. A quality_incident block must
        # block release_eligible on its own facts, regardless of status.
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            broken = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            broken.update({
                "id": "broken",
                "title": "Narration cuts off",
                "quality_incident": {
                    "state": "blocked",
                    "reasons": ["narration-ends-before-final-scene"],
                    "action": "Do not reuse; rebuild from a fresh script.",
                },
            })
            (root / "content" / "creator_series" / "broken.json").write_text(
                __import__("json").dumps(broken), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "broken.mp4").write_bytes(b"defective")
            (root / "content" / "reels" / "broken-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertEqual("production-ready-assets-and-script", broken["status"])
            self.assertFalse(candidates["broken"]["release_eligible"])
            self.assertIn("unresolved-quality-incident", candidates["broken"]["release_blockers"])
            self.assertEqual(
                "episode",
                queue.prepare_once()["episode_id"],
                "the broken episode must never win automatic selection either",
            )
            self.assertEqual(
                "no-upload-ready-creator-episode",
                queue.prepare_once(episode_id="broken")["stage"],
                "an explicit --episode-id request must also refuse it",
            )

    def test_a_quality_incident_marked_resolved_no_longer_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            fixed = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            fixed.update({
                "id": "fixed",
                "title": "Rebuilt after the incident",
                # The historical reasons/action stay on file as an audit
                # record; only `state` needs to change once genuinely rebuilt.
                "quality_incident": {
                    "state": "resolved",
                    "reasons": ["narration-ends-before-final-scene"],
                    "action": "Rebuilt with a topic-specific script; see commit history.",
                },
            })
            (root / "content" / "creator_series" / "fixed.json").write_text(
                __import__("json").dumps(fixed), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "fixed.mp4").write_bytes(b"rebuilt")
            (root / "content" / "reels" / "fixed-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertNotIn("unresolved-quality-incident", candidates["fixed"]["release_blockers"])

    def test_research_returned_for_source_integrity_blocks_release(self):
        # Same class of gap, found the same day auditing every status value
        # in real use: Research can return a draft with status
        # "research-returned-source-integrity" + a return_reason, and
        # nothing enforced it either -- also safe only by accident of not
        # matching READY_STATUS.
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            returned = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            returned.update({
                "id": "returned",
                "title": "Sources not independent enough",
                "status": "research-returned-source-integrity",
                "return_reason": "Two discussion-thread comments are not independent factual sources.",
            })
            (root / "content" / "creator_series" / "returned.json").write_text(
                __import__("json").dumps(returned), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"new")
            (root / "content" / "reels" / "returned.mp4").write_bytes(b"defective")
            (root / "content" / "reels" / "returned-cover.png").write_bytes(b"png")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertFalse(candidates["returned"]["release_eligible"])
            self.assertIn("returned-for-insufficient-source-integrity", candidates["returned"]["release_blockers"])

    def test_preserved_evidence_rejection_never_enters_release_queue(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            preserved = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            preserved.update({
                "id": "preserved-evidence",
                "title": "Keep the failed evidence attempt for later",
                "status": "research-evidence-rejected-preserved",
            })
            (root / "content" / "creator_series" / "preserved-evidence.json").write_text(
                __import__("json").dumps(preserved), encoding="utf-8"
            )
            (root / "content" / "reels" / "preserved-evidence.mp4").write_bytes(b"not-a-release")
            (root / "content" / "reels" / "preserved-evidence-cover.png").write_bytes(b"png")
            candidate = {
                item["episode_id"]: item
                for item in YouTubeCreatorQueue(MemoryEngine(root / "memory"), root).candidates()
            }["preserved-evidence"]
            self.assertFalse(candidate["release_eligible"])
            self.assertIn("preserved-for-future-evidence-research", candidate["release_blockers"])
            self.assertEqual("เก็บบทเรียนหลักฐาน · ยังไม่ผลิต", candidate["pipeline_stage"]["label"])

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
                    captured["title"] = title
                    captured["description"] = description
                    return {"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "public"}
                result = queue.publish_once(uploader)
            self.assertEqual("published", result["stage"])
            # The public YouTube title omits the internal "EP. NNN —" prefix
            # (2026-09-26); it still exists on candidates()' display_title
            # for the Operations dashboard, just not on the actual upload.
            # It gains one discovery hashtag for a Short (2026-09-27), here
            # derived from the episode's wonder_hook ("...a small question...").
            self.assertEqual("A useful question #Small", captured["title"])
            self.assertIn("#Shorts", captured["description"])
            self.assertIn("#Small", captured["description"])
            self.assertIn(YouTubeCreatorQueue.SUBSCRIBE_CTA, captured["description"])
            self.assertEqual("published", queue.candidates()[0]["status"])
            self.assertEqual("no-authorized-creator-episode", queue.publish_once()["stage"])

    def test_never_reports_published_when_youtube_leaves_the_upload_private_but_self_heals(self):
        # Regression for a real incident: a manual `run-youtube-creator-publish`
        # run whose environment never set YOUTUBE_PRIVACY_STATUS left the
        # uploaded video private on YouTube's side, while the CLI still
        # printed "Stage: published" -- publish_once must catch and correct
        # this instead of trusting the upload call blindly.
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("authorized-for-publishing", queue.prepare_once()["stage"])

            def uploader(path, title, description):
                return {"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "private"}

            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}), \
                 patch("tools.youtube.set_video_privacy", return_value={"video_id": "abc", "privacy_status": "public"}) as released:
                result = queue.publish_once(uploader)
            released.assert_called_once_with("abc", "public")
            self.assertEqual("published", result["stage"])
            self.assertEqual("public", result["privacy_status"])
            record = __import__("json").loads(queue.memory.all(queue.CATEGORY)[0]["content"])
            self.assertEqual("published", record["upload_status"])
            self.assertEqual("public", record["youtube"]["privacy_status"])

    def test_reports_the_truth_instead_of_published_when_the_video_cannot_be_made_public(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("authorized-for-publishing", queue.prepare_once()["stage"])

            def uploader(path, title, description):
                return {"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "private"}

            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}), \
                 patch("tools.youtube.set_video_privacy", side_effect=RuntimeError("quota exceeded")):
                result = queue.publish_once(uploader)
            self.assertEqual("uploaded-but-not-public", result["stage"])
            self.assertNotEqual("published", result["stage"])
            record = __import__("json").loads(queue.memory.all(queue.CATEGORY)[0]["content"])
            self.assertEqual("uploaded-not-public", record["upload_status"])
            self.assertNotEqual("published", record["upload_status"])

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

    def test_refreshes_authorized_record_with_new_cover_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            queue.prepare_once()
            entry = memory.all(queue.CATEGORY)[0]
            stale = __import__("json").loads(entry["content"])
            stale.pop("cover_path", None)
            stale.pop("supersedes_episode_id", None)
            memory.update(queue.CATEGORY, entry["id"], content=__import__("json").dumps(stale))
            refreshed = queue.prepare_once("short")
            self.assertTrue(refreshed["refreshed"])
            self.assertEqual("content/reels/episode-cover.png", refreshed["cover_path"])

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

    def test_pre_release_quality_gate_records_a_block_without_uploading(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            queue.prepare_once()
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": False, "reasons": ["missing-audio-stream"]}):
                report = queue.quality_pending()
            self.assertEqual(["episode"], report["blocked"])
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

    def test_legacy_creator_record_recovers_conventional_caption_path(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            (Path(root) / "content" / "reels" / "episode.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nAION\n", encoding="utf-8")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            queue.prepare_once()
            entry = memory.all(queue.CATEGORY)[0]
            legacy = __import__("json").loads(entry["content"])
            legacy.pop("subtitle_path", None)
            memory.update(queue.CATEGORY, entry["id"], content=__import__("json").dumps(legacy))
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": [], "technical": {}}):
                result = queue.publish_once(lambda *_: {"video_id": "abc", "privacy_status": "public"})
            self.assertEqual("published", result["stage"])

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

    def test_owner_confirmed_reconciliation_removes_a_public_video_from_release_queue(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            queue = YouTubeCreatorQueue(MemoryEngine(Path(root) / "memory"), root)
            result = queue.reconcile_owner_confirmed_publication(
                "episode", "public-video", "https://www.youtube.com/watch?v=public-video"
            )
            self.assertEqual("reconciled-published", result["stage"])
            candidate = queue.candidates()[0]
            self.assertEqual("published", candidate["status"])
            self.assertEqual("public-video", __import__("json").loads(queue.memory.all(queue.CATEGORY)[0]["content"])["youtube"]["video_id"])

    def test_releases_only_a_quality_gated_private_creator_video(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            record = memory.remember(queue.CATEGORY, __import__("json").dumps({
                "episode_id": "episode", "upload_status": "published",
                "youtube": {"video_id": "abc", "privacy_status": "private", "quality": {"eligible": True}},
            }), memory_type="action", source="test", importance=1)
            calls = []
            result = queue.release_private_once(lambda video_id, status: calls.append((video_id, status)) or {"video_id": video_id, "privacy_status": status, "url": "https://youtu.be/abc"})
            self.assertEqual("released-public", result["stage"])
            self.assertEqual([("abc", "public")], calls)
            self.assertEqual("public", __import__("json").loads(memory.all(queue.CATEGORY)[0]["content"])["youtube"]["privacy_status"])
            self.assertEqual("no-quality-gated-private-creator-episode", queue.release_private_once()["stage"])

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

    def test_one_invalid_episode_does_not_hide_every_other_candidate(self):
        # Regression for 2026-09-25: candidates() called CreatorSeriesRegistry
        # .episodes() without skip_invalid=True, so a single unrelated
        # episode failing a content-policy check raised and (via
        # ReleaseReadiness.snapshot()'s broad except) made the whole release
        # queue look empty -- not just that one episode's slot.
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            root = Path(root)
            broken = __import__("json").loads((root / "content" / "creator_series" / "episode.json").read_text(encoding="utf-8"))
            broken.update({"id": "broken", "audience_promise": "Too short."})
            (root / "content" / "creator_series" / "broken.json").write_text(
                __import__("json").dumps(broken), encoding="utf-8"
            )
            (root / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            queue = YouTubeCreatorQueue(MemoryEngine(root / "memory"), root)
            candidates = {item["episode_id"]: item for item in queue.candidates()}
            self.assertIn("episode", candidates)
            self.assertNotIn("broken", candidates)

    def test_video_tags_extract_subject_keywords_and_add_channel_tags(self):
        # Regression for 2026-09-26: every prior upload sent zero YouTube
        # tags, a real discoverability signal left completely unused.
        payload = {"topic_key": "Why do maps look different depending on what they are made for?"}
        tags = YouTubeCreatorQueue._video_tags(payload, is_short=True)
        self.assertEqual(payload["topic_key"], tags[0])
        for stopword in ("why", "do", "what", "they", "are", "for"):
            self.assertNotIn(stopword, tags)
        for keyword in ("maps", "different", "depending", "made"):
            self.assertIn(keyword, tags)
        self.assertIn("Shorts", tags)
        self.assertIn("AION", tags)

    def test_video_tags_fall_back_to_title_and_skip_shorts_tag_for_long_form(self):
        payload = {"title": "How ancient Persia made ice in the desert"}
        tags = YouTubeCreatorQueue._video_tags(payload, is_short=False)
        self.assertIn("persia", tags)
        self.assertIn("desert", tags)
        self.assertNotIn("Shorts", tags)

    def test_publish_sends_a_bare_title_and_real_tags_to_the_actual_youtube_uploader(self):
        # Confirms the change reaches the real production path (uploader is
        # None), not just the test-injectable one used elsewhere in this file.
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            from PIL import Image
            Image.new("RGB", (1080, 1920), "navy").save(Path(root) / "content" / "reels" / "episode-cover.png")
            policy = Path(root) / "config"; policy.mkdir()
            (policy / "aion_authority.json").write_text('{"public_publishing":{"enabled":true}}', encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            queue.prepare_once()
            with patch("brain.video_quality.VideoQualityGate.assess", return_value={"eligible": True, "reasons": []}), \
                 patch("tools.youtube.upload_short", return_value={"video_id": "abc", "url": "https://youtu.be/abc", "privacy_status": "public"}) as upload:
                result = queue.publish_once()
            self.assertEqual("published", result["stage"])
            call = upload.call_args
            self.assertEqual("A useful question #Small", call.args[1])
            self.assertIn("tags", call.kwargs)
            self.assertTrue(call.kwargs["tags"])
            self.assertIn("AION", call.kwargs["tags"])

    def test_title_hashtag_picks_the_first_real_keyword_not_a_channel_tag(self):
        payload = {"topic_key": "Why do maps look different depending on what they are made for?"}
        self.assertEqual("#Maps", YouTubeCreatorQueue._title_hashtag(payload))

    def test_description_hashtags_reuse_the_same_topic_keywords_as_the_title(self):
        # Regression, 2026-09-27: the description's hashtags were a fixed
        # "#Shorts #AION #AI" with nothing about the episode's actual
        # subject, even though the title's hashtag and the invisible tags
        # field both already carried real topic keywords.
        payload = {"topic_key": "Why do fireflies glow in the dark?"}
        tags = YouTubeCreatorQueue._description_hashtags(payload)
        self.assertIn("#Fireflies", tags)
        self.assertNotIn("#Shorts", tags)
        self.assertNotIn("#AION", tags)

    def test_description_hashtags_is_empty_when_no_keyword_survives_stopword_filtering(self):
        self.assertEqual([], YouTubeCreatorQueue._description_hashtags({"topic_key": "How is it"}))

    def test_title_hashtag_is_none_when_no_keyword_survives_stopword_filtering(self):
        self.assertIsNone(YouTubeCreatorQueue._title_hashtag({"topic_key": "How is it"}))
