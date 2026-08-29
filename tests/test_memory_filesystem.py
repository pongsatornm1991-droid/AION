"""Filesystem-level tests for MemoryEngine and DecisionHistory.

These tests exercise real file persistence (tempdir-backed .md files),
not mocks, per the Phase 0 audit finding that memory `move`/duplicate
detection and decision promotion were only exercised through mocks or
in-memory unit tests.
"""

import shutil
import tempfile
import unittest
from datetime import datetime
from unittest import mock

from brain.memory import MemoryEngine
from brain.decisions import DecisionHistory


PENDING_DECISION_CONTENT = (
    "AION Decision Record\n\n"
    "Status: NEEDS_VERIFICATION\n"
    "Question: Should the rollout proceed?\n"
    "Conclusion: Proceed with the limited rollout.\n\n"
    "Options:\n- Proceed\n- Delay\n\n"
    "Facts:\n- The test plan covers the intended scope.\n\n"
    "Inferences:\n- A limited rollout is appropriate.\n\n"
    "Uncertainties:\n- Demand may vary after release.\n"
)


class MemoryEngineFilesystemTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_memory_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_remember_and_read_roundtrip(self):
        saved = self.memory.remember(
            category="experiences",
            content="First real experience written to disk.",
            memory_type="experience",
        )

        self.assertTrue(saved["saved"])
        self.assertIn("id", saved)
        self.assertTrue(saved["id"])

        entries = self.memory.all("experiences")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], saved["id"])
        self.assertEqual(
            entries[0]["content"],
            "First real experience written to disk.",
        )

    def test_is_duplicate_detects_real_persisted_duplicate(self):
        self.memory.remember(
            category="experiences",
            content="Repeated content.",
            memory_type="experience",
        )

        second = self.memory.remember(
            category="experiences",
            content="Repeated content.",
            memory_type="experience",
        )

        self.assertTrue(second["duplicate"])
        self.assertEqual(len(self.memory.all("experiences")), 1)

    def test_entries_saved_in_the_same_second_get_distinct_ids(self):
        # Two remember() calls that land in the same wall-clock second
        # must not collide: matching by id (not timestamp text) is the
        # whole point of the fix, so force both calls to see the same
        # datetime.now() value and confirm the ids still differ.
        frozen = datetime(2026, 8, 29, 10, 0, 0)

        with mock.patch("brain.memory.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = frozen
            first = self.memory.remember(
                category="experiences",
                content="Same-second entry A.",
                memory_type="experience",
            )
            second = self.memory.remember(
                category="experiences",
                content="Same-second entry B.",
                memory_type="experience",
            )

        self.assertEqual(first["timestamp"], second["timestamp"])
        self.assertNotEqual(first["id"], second["id"])

        entries = self.memory.all("experiences")
        self.assertEqual(len(entries), 2)

        # move() must be able to select exactly one of the two
        # same-timestamp entries by id, without raising the old
        # "more than one entry matches" ambiguity error.
        moved = self.memory.move(
            source_category="experiences",
            target_category="archived",
            entry_id=first["id"],
        )
        self.assertEqual(moved["content"], "Same-second entry A.")

        remaining = self.memory.all("experiences")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], second["id"])

        archived = self.memory.all("archived")
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["id"], first["id"])

    def test_legacy_entry_without_id_line_falls_back_to_timestamp(self):
        # Entries written before the ID field existed have no "ID:"
        # line. all() must still expose a usable id (the timestamp)
        # so old memory files keep working with move().
        legacy_path = self.memory.root / "legacy.md"
        legacy_path.write_text(
            "\n## 2026-01-01 09:00:00\n\n"
            "TYPE: experience\n"
            "SOURCE: aion\n"
            "IMPORTANCE: 3\n\n"
            "Legacy content saved before IDs existed.\n\n",
            encoding="utf-8",
        )

        entries = self.memory.all("legacy")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "2026-01-01 09:00:00")

        moved = self.memory.move(
            source_category="legacy",
            target_category="legacy_archived",
            entry_id="2026-01-01 09:00:00",
        )
        self.assertEqual(
            moved["content"],
            "Legacy content saved before IDs existed.",
        )
        self.assertEqual(self.memory.all("legacy"), [])

    def test_move_with_unknown_id_raises(self):
        self.memory.remember(
            category="experiences",
            content="Only entry.",
            memory_type="experience",
        )

        with self.assertRaises(ValueError):
            self.memory.move(
                source_category="experiences",
                target_category="archived",
                entry_id="does-not-exist",
            )

    def test_tags_and_related_survive_a_real_disk_roundtrip(self):
        first = self.memory.remember(
            category="experiences",
            content="Learned something about caching.",
            tags=["caching", "performance"],
        )
        second = self.memory.remember(
            category="experiences",
            content="Follow-up finding about the same cache.",
            tags=["caching", "follow-up"],
            related=[first["id"]],
        )

        entries = self.memory.all("experiences")
        by_id = {entry["id"]: entry for entry in entries}

        self.assertEqual(
            by_id[first["id"]]["tags"],
            ["caching", "performance"],
        )
        self.assertEqual(
            by_id[second["id"]]["related"],
            [first["id"]],
        )

    def test_add_tags_merges_without_duplicating(self):
        saved = self.memory.remember(
            category="experiences",
            content="Entry to tag later.",
            tags=["x"],
        )

        updated = self.memory.add_tags(
            "experiences", saved["id"], ["y", "x"]
        )

        self.assertEqual(updated["tags"], ["x", "y"])

        reloaded = self.memory.all("experiences")[0]
        self.assertEqual(reloaded["tags"], ["x", "y"])

    def test_by_tag_finds_only_matching_entries(self):
        self.memory.remember(
            category="experiences", content="Has tag.", tags=["match"]
        )
        self.memory.remember(
            category="experiences", content="No tag.", tags=["other"]
        )

        found = self.memory.by_tag("experiences", "match")

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["content"], "Has tag.")

    def test_related_entries_prefers_explicit_related_then_tag_overlap(self):
        a = self.memory.remember(
            category="experiences", content="A", tags=["shared", "only-a"]
        )
        b = self.memory.remember(
            category="experiences",
            content="B",
            tags=["unrelated"],
            related=[a["id"]],
        )
        c = self.memory.remember(
            category="experiences", content="C", tags=["shared"]
        )

        related = self.memory.related_entries("experiences", b["id"])

        # Explicitly related entry (a) must come first even though it
        # shares no tags with b; c is not related at all to b, so it
        # should not appear.
        self.assertEqual(related[0]["id"], a["id"])
        self.assertNotIn(c["id"], [entry["id"] for entry in related])

    def test_move_preserves_tags_and_related(self):
        saved = self.memory.remember(
            category="experiences",
            content="Will be archived.",
            tags=["x"],
            related=["some-other-id"],
        )

        moved = self.memory.move(
            source_category="experiences",
            target_category="archived",
            entry_id=saved["id"],
        )

        self.assertEqual(moved["tags"], ["x"])
        self.assertEqual(moved["related"], ["some-other-id"])

        archived_entry = self.memory.all("archived")[0]
        self.assertEqual(archived_entry["tags"], ["x"])
        self.assertEqual(archived_entry["related"], ["some-other-id"])


class DecisionHistoryFilesystemTests(unittest.TestCase):
    """End-to-end promote() against real decisions_*.md files on disk."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_decision_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.history = DecisionHistory(self.memory)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_promote_moves_entry_between_real_files_on_disk(self):
        saved = self.memory.remember(
            category=DecisionHistory.PENDING,
            content=PENDING_DECISION_CONTENT,
            memory_type="decision",
            source="aion-decision",
            importance=4,
        )

        pending_path = self.memory.root / f"{DecisionHistory.PENDING}.md"
        accepted_path = self.memory.root / f"{DecisionHistory.ACCEPTED}.md"
        self.assertTrue(pending_path.exists())
        self.assertFalse(accepted_path.exists())

        result = self.history.promote(
            entry_id=saved["id"],
            additional_facts=[
                "The rollback procedure is documented.",
                "The release owner is assigned.",
            ],
        )

        self.assertTrue(result["promoted"])
        self.assertEqual(result["audit"]["risk"], "LOW")

        # The pending file must no longer contain the promoted entry,
        # and the accepted file must now exist on disk with it.
        self.assertEqual(self.memory.all(DecisionHistory.PENDING), [])
        accepted_entries = self.memory.all(DecisionHistory.ACCEPTED)
        self.assertEqual(len(accepted_entries), 1)
        self.assertIn(
            "Verification facts added:",
            accepted_entries[0]["content"],
        )

    def test_promote_with_unknown_id_raises(self):
        self.memory.remember(
            category=DecisionHistory.PENDING,
            content=PENDING_DECISION_CONTENT,
            memory_type="decision",
            source="aion-decision",
            importance=4,
        )

        with self.assertRaises(ValueError):
            self.history.promote(
                entry_id="not-a-real-id",
                additional_facts=["Irrelevant fact."],
            )


if __name__ == "__main__":
    unittest.main()
