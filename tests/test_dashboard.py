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
            self.assertEqual(7, len(snapshot["creator_library"]))
            self.assertEqual("ready", snapshot["creator_library"][0]["status"])
            self.assertEqual("AION Wonders", snapshot["creator_program"][0]["series"])
            self.assertEqual("ready-to-listen", snapshot["creator_autonomy"]["status"])

    def test_a_legacy_string_action_record_never_crashes_the_dashboard(self):
        # Real production bug (found 2026-09-04): tools/dashboard.py's
        # _reel_summary() assumed every published_reels record's "action"/
        # "platform_actions" field was always a dict, and every "youtube"
        # field was always a dict too. A historical record predating the
        # multi-platform {"instagram": ..., "facebook": ...} shape crashed
        # every hourly run of publish-public-summary.yml with
        # AttributeError: 'str' object has no attribute 'get' -- silently
        # freezing the public AION Pulse page's "AION's actual thinking"
        # section since the day that workflow was added. This mirrors the
        # exact defensive fix brain/growth_pulse.py already applies to the
        # same category (see tests/test_growth_pulse.py).
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "published_reels",
                json.dumps({"action": "some-legacy-action-id"}),
                "action",
            )
            memory.remember(
                "published_reels",
                json.dumps({
                    "platform_actions": {"instagram": "ig-2"},
                    "youtube": "not-a-dict-either",
                }),
                "action",
            )
            memory.remember(
                "published_reels",
                json.dumps("a bare string record, not even an object"),
                "action",
            )
            memory.remember(
                "published_reels",
                json.dumps({
                    "platform_actions": {"instagram": "ig-3", "facebook": "fb-3"},
                    "youtube": {"video_id": "yt-3"},
                }),
                "action",
            )

            snapshot = build_snapshot(root)

            self.assertEqual(
                {"instagram": 2, "facebook": 1, "youtube": 1},
                snapshot["content"]["platform_counts"],
            )
