import json
import tempfile
import unittest

from brain.memory import MemoryEngine
from tools.dashboard import build_snapshot


class DashboardTests(unittest.TestCase):
    def test_snapshot_combines_platforms_and_mind(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("lessons", "AION learned to check evidence.", "lesson")
            memory.remember("questions", "What should I learn next?", "question")
            memory.remember(
                "social_feedback",
                json.dumps({"kind": "account", "followers_count": 12, "media_count": 3}),
                "observation",
                source="instagram-feedback",
            )
            memory.remember(
                "published_reels",
                json.dumps({
                    "caption": "AION is learning in public.",
                    "platform_actions": {"instagram": "ig", "facebook": "fb"},
                    "youtube": {"video_id": "yt"},
                }),
                "action",
            )

            snapshot = build_snapshot(root)

            self.assertEqual(12, snapshot["platforms"]["instagram"]["followers"])
            self.assertEqual(1, snapshot["platforms"]["facebook"]["reels_published"])
            self.assertEqual(1, snapshot["platforms"]["youtube"]["shorts_published"])
            self.assertEqual(1, snapshot["mind"]["lessons"])
            self.assertEqual(1, snapshot["mind"]["questions"])
            self.assertEqual(4, len(snapshot["state_council"]["states"]))
            self.assertTrue(snapshot["brain"]["nodes"])
