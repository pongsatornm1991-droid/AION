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
                render_reel("A hook", "A thought", output, duration=12)
            command = run.call_args.args[0]
            self.assertIn("apad=pad_dur=12", " ".join(command))
            self.assertNotIn("-shortest", command)
            self.assertIn("+faststart", command)


if __name__ == "__main__":
    unittest.main()
