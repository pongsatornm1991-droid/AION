"""Offline tests for tools/publish_public_summary.py -- the redacted
public-facing summary built for the AION Pulse status page (2026-09-03).

Never touches a real memory root or the network: every test builds an
isolated tempdir MemoryEngine (same pattern as tests/test_dashboard.py),
so this suite proves the allowlist behavior on its own, real terms --
most importantly, that anything NOT on the explicit allowlist (a raw
comment_replies entry, an internal memory id, a full snapshot field
this module doesn't know about) never survives into the public
output, even if a future build_snapshot() change starts returning it.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from brain.memory import MemoryEngine
from tools.dashboard import build_snapshot
from tools.publish_public_summary import build_public_summary


class BuildPublicSummaryTests(unittest.TestCase):
    def _snapshot_with(self, populate):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            populate(memory)
            return build_snapshot(root)

    def test_allowlisted_fields_survive(self):
        snapshot = self._snapshot_with(lambda memory: (
            memory.remember("lessons", "AION learned to check evidence.", "lesson"),
            memory.remember("questions", "What should I learn next?", "question"),
        ))

        summary = build_public_summary(snapshot)

        self.assertEqual(1, summary["mind"]["lessons"])
        self.assertEqual(1, summary["mind"]["questions"])
        self.assertTrue(any(t["category"] == "Lesson" for t in summary["thoughts"]))
        self.assertIn("generated_at", summary)

    def test_comment_replies_never_reach_the_public_summary(self):
        # comment_replies holds real Facebook users' names and comment
        # text -- build_snapshot() already never reads this category
        # for anything it returns, but this test guards the actual
        # promise this module makes: even if that ever changed, the
        # allowlist here has no path for a "comment_replies" category
        # to reach the public JSON.
        snapshot = self._snapshot_with(lambda memory: memory.remember(
            "comment_replies",
            json.dumps({"commenter": "Somchai R.", "comment": "อยากรู้ราคาเลยครับ", "reply": "..."}),
            "action",
        ))

        summary = build_public_summary(snapshot)

        dumped = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("Somchai", dumped)
        self.assertNotIn("comment_replies", dumped)
        self.assertEqual([], summary["thoughts"])

    def test_unknown_snapshot_fields_are_dropped_not_passed_through(self):
        # The allowlist is a copy-out, not a pass-through -- a stray
        # top-level field a future build_snapshot() might add (say,
        # something genuinely private) must not silently appear here
        # just because it exists on the snapshot dict.
        snapshot = build_snapshot(tempfile.mkdtemp())
        snapshot["something_new_and_sensitive"] = "should never leak"

        summary = build_public_summary(snapshot)

        self.assertNotIn("something_new_and_sensitive", summary)
        self.assertNotIn("something_new_and_sensitive", json.dumps(summary))

    def test_recent_posts_carry_only_the_already_public_fields(self):
        snapshot = self._snapshot_with(lambda memory: memory.remember(
            "published_reels",
            json.dumps({
                "caption": "AION is learning in public.",
                "platform_actions": {"instagram": "ig", "facebook": "fb"},
                "youtube": {"video_id": "yt"},
            }),
            "action",
        ))

        summary = build_public_summary(snapshot)

        self.assertEqual(1, len(summary["recent_posts"]))
        post = summary["recent_posts"][0]
        self.assertEqual("AION is learning in public.", post["caption"])
        self.assertTrue(post["instagram"] and post["facebook"] and post["youtube"])
        self.assertEqual({"timestamp", "caption", "instagram", "facebook", "youtube"}, set(post.keys()))

    def test_mood_carries_its_own_honesty_disclaimer(self):
        # state_council's "disclaimer" line (this is a computed signal
        # from memory/activity, never a claim AION has real feelings)
        # must always travel with the mood scores on the public page --
        # dropping it here while keeping the mood values would be the
        # one way this summary could misrepresent AION, so it is
        # explicitly asserted, not just carried along by accident.
        snapshot = build_snapshot(tempfile.mkdtemp())
        summary = build_public_summary(snapshot)
        self.assertTrue(summary["state_council"]["disclaimer"])
        self.assertIn(summary["state_council"]["dominant"],
                       [s["key"] for s in summary["state_council"]["states"]])

    def test_default_build_uses_live_snapshot(self):
        # No snapshot passed in -- build_public_summary() must call
        # build_snapshot() itself with no arguments, which then falls
        # back to AION_MEMORY_ROOT (or "memory" if that is unset), same
        # default as everywhere else in this codebase. Pointed at an
        # isolated tempdir here -- same reason as every other test in
        # this suite that needs a real memory root (see
        # tests/test_decision_auditor.py's own comment on this): this
        # local device's own "memory" folder is a broken OneDrive
        # symlink, unrelated to anything this module does.
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(os.environ, {"AION_MEMORY_ROOT": root}):
                summary = build_public_summary()
        self.assertIn("generated_at", summary)
        self.assertIn("mind", summary)


if __name__ == "__main__":
    unittest.main()
