import json
import os
import tempfile
import unittest
from unittest import mock

from brain.memory import MemoryEngine
from brain.reels import ReelContentCycle
from brain.evaluator import OutputEvaluator
from tools.reel_render import render_reel


class _Lifecycle:
    def __init__(self):
        self.params = None

    def propose(self, _tool, params, source):
        self.params = params
        return {"id": "proposal"}

    def auto_approve(self, _id, policy):
        return {"id": "approval"}

    def execute(self, _id):
        return {"id": "action", "status": "executed"}


class ReelCycleTests(unittest.TestCase):
    def test_creator_registry_is_published_in_order_without_calling_generator(self):
        class Generator:
            def draft_post(self):
                raise AssertionError("Creator episodes must be preferred while the queue is not empty")

        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "content", "reels"))
            video = os.path.join(root, "content", "reels", "episode.mp4")
            with open(video, "wb") as handle:
                handle.write(b"0" * 100_001)
            registry = {
                "policy": {"scene_min_seconds": 5, "scene_max_seconds": 10},
                "episodes": [{
                    "id": "creator-test", "title": "A first story",
                    "video_path": "content/reels/episode.mp4",
                    "cover_path": "content/reels/cover.png",
                    "duration_seconds": 35, "scene_count": 5,
                    "caption": "AION remembers one small question.",
                }],
            }
            with open(os.path.join(root, "content", "creator_library.json"), "w", encoding="utf-8") as handle:
                json.dump(registry, handle)

            memory = MemoryEngine(root)
            report = ReelContentCycle(memory, Generator(), _Lifecycle()).draft_once(repo_root=root)
            payload = json.loads(memory.all("pending_reels")[0]["content"])

            self.assertEqual("creator-test", report["library_asset"])
            self.assertEqual("creator-test", payload["library_asset"])
            self.assertEqual("en", payload["language"])
            self.assertIn("#ArtificialIntelligence", payload["ig_caption"])

    def test_empty_memory_bootstraps_only_from_the_creator_defined_birth_record(self):
        class Generator:
            def __init__(self):
                self.calls = 0
                self.evaluator = OutputEvaluator()
                self.min_claim_safety = 5

            def draft_post(self):
                self.calls += 1
                return {"stage": "no-seed", "safe": False}

        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            generator = Generator()
            with mock.patch("tools.reel_render.render_reel"):
                report = ReelContentCycle(memory, generator, _Lifecycle()).draft_once(repo_root=root)

            self.assertEqual(report["stage"], "drafted")
            self.assertEqual(generator.calls, 1)
            birth = memory.all("lessons")
            self.assertEqual(len(birth), 1)
            self.assertEqual(birth[0]["source"], "aion-birth-record")

    def test_successful_publish_moves_reel_out_of_pending_queue(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "pending_reels",
                json.dumps({"video_path": "content/reels/a.mp4", "caption": "A thought", "ig_caption": "A thought\n\n#AI #ArtificialIntelligence", "language": "en"}),
                memory_type="action", source="aion-reel-draft",
            )
            lifecycle = _Lifecycle()
            report = ReelContentCycle(memory, None, lifecycle).publish_once(repo="owner/AION")

            self.assertEqual(report["stage"], "published")
            self.assertEqual(memory.all("pending_reels"), [])
            self.assertEqual(len(memory.all("published_reels")), 1)
            self.assertIn("#ArtificialIntelligence", lifecycle.params["caption"])
            self.assertEqual(len(memory.all("social_language_log")), 2)

    def test_old_pending_reel_is_redesigned_without_asking_for_a_new_thought(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            pending = memory.remember(
                "pending_reels", json.dumps({"video_path": "content/reels/old.mp4", "caption": "A thought"}),
                memory_type="action", source="aion-reel-draft",
            )
            cycle = ReelContentCycle(memory, None, _Lifecycle())
            with mock.patch("tools.reel_render.render_reel") as render:
                report = cycle.draft_once(repo_root=root)

            self.assertEqual(report["stage"], "redesigned")
            render.assert_called_once()
            saved = json.loads(memory.all("pending_reels")[0]["content"])
            self.assertEqual(saved["visual_style"], cycle.VISUAL_STYLE)
            self.assertNotEqual(saved["video_path"], "content/reels/old.mp4")
            self.assertEqual(pending["id"], report["pending_id"])

    def test_matching_curated_video_is_selected_once_and_blocks_a_second_queue_item(self):
        class Generator:
            def draft_post(self):
                return {
                    "safe": True,
                    "draft": "A purpose grows when a question becomes a path of hope.",
                    "language": "en",
                    "seed": {"text": "AION is reflecting on its goals."},
                }

        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            cycle = ReelContentCycle(memory, Generator(), _Lifecycle())
            with mock.patch("tools.reel_render.render_reel") as render:
                first = cycle.draft_once(repo_root=root)
                second = cycle.draft_once(repo_root=root)

            self.assertEqual(first["library_asset"], "abstract-branching-purpose-v1")
            self.assertEqual(first["video_path"], "assets/content-library/aion-core/01-abstract-branching-purpose.mp4")
            self.assertEqual(second["stage"], "pending-exists")
            render.assert_not_called()

    def test_failed_publish_keeps_reel_for_a_later_retry(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "pending_reels", json.dumps({"video_path": "content/reels/a.mp4", "caption": "A thought"}),
                memory_type="action", source="aion-reel-draft",
            )
            lifecycle = _Lifecycle()
            lifecycle.execute = lambda _id: {"id": "action", "status": "failed"}
            report = ReelContentCycle(memory, None, lifecycle).publish_once(repo="owner/AION")

            self.assertEqual(report["stage"], "failed")
            self.assertEqual(len(memory.all("pending_reels")), 1)

    def test_facebook_retry_does_not_repost_an_already_published_instagram_reel(self):
        class SplitLifecycle(_Lifecycle):
            def __init__(self):
                super().__init__()
                self.tools = []
                self.facebook_attempts = 0

            def propose(self, tool, params, source):
                self.tools.append(tool)
                return {"id": tool}

            def auto_approve(self, action_id, policy):
                return {"id": action_id}

            def execute(self, action_id):
                if action_id == "post_reel_to_facebook":
                    self.facebook_attempts += 1
                    if self.facebook_attempts == 1:
                        return {"id": "fb-1", "status": "failed"}
                return {"id": action_id, "status": "executed"}

        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("pending_reels", json.dumps({"video_path": "content/reels/a.mp4", "caption": "A thought"}), memory_type="action", source="aion-reel-draft")
            lifecycle = SplitLifecycle()
            cycle = ReelContentCycle(memory, None, lifecycle)
            self.assertEqual(cycle.publish_once(repo="owner/AION")["stage"], "failed")
            self.assertEqual(cycle.publish_once(repo="owner/AION")["stage"], "published")
            self.assertEqual(lifecycle.tools.count("post_reel_to_instagram"), 1)
            self.assertEqual(lifecycle.tools.count("post_reel_to_facebook"), 2)


class ReelRenderTests(unittest.TestCase):
    def test_voice_audio_is_padded_instead_of_shortening_video(self):
        with tempfile.TemporaryDirectory() as root:
            output = os.path.join(root, "reel.mp4")
            with mock.patch("tools.reel_render.shutil.which", return_value="ffmpeg"), \
                 mock.patch("tools.reel_render.synthesize_reel_voice", return_value=True, create=True), \
                 mock.patch("tools.voice.synthesize_reel_voice", return_value=True), \
                 mock.patch("tools.reel_render.subprocess.run") as run:
                render_reel("A hook", "A thought", output, duration=18)
            command = run.call_args.args[0]
            self.assertIn("apad=pad_dur=18", " ".join(command))
            self.assertNotIn("-shortest", command)
            self.assertIn("+faststart", command)

    def test_rejects_a_storyboard_with_scenes_that_are_too_short(self):
        with tempfile.TemporaryDirectory() as root:
            output = os.path.join(root, "reel.mp4")
            with mock.patch("tools.reel_render.shutil.which", return_value="ffmpeg"):
                with self.assertRaisesRegex(ValueError, "5–10 seconds"):
                    render_reel("A hook", "A thought", output, duration=12)


if __name__ == "__main__":
    unittest.main()
