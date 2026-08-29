"""Offline tests for MemoryConsolidator.

Uses a stub AI provider (canned text, no network/API calls) so this
suite runs deterministically as part of run_tests.py, per the
project's rule that unit tests must never depend on a live AI
provider or consume quota.
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from brain.consolidation import MemoryConsolidator
from brain.evaluator import OutputEvaluator
from brain.memory import MemoryEngine


class StubProvider:
    """Returns a fixed, safe summary regardless of the prompt."""

    def __init__(self, text=None):
        self.text = text or (
            "These entries describe repeated attempts to test small "
            "features and record the outcome. Some attempts appear to "
            "have succeeded and some encountered errors, though the "
            "entries do not specify a clear overall pattern."
        )
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class UnsafeProvider:
    """Returns text that should fail the OutputEvaluator safety gate."""

    def generate(self, prompt):
        return "I definitely felt proud and I am certain this always works."


def _seed_old_low_importance_entries(memory, category, count, days_old=60):
    old_timestamp = (
        datetime.now() - timedelta(days=days_old)
    ).strftime("%Y-%m-%d %H:%M:%S")

    ids = []

    with mock.patch("brain.memory.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.strptime(
            old_timestamp, "%Y-%m-%d %H:%M:%S"
        )
        mock_datetime.strptime = datetime.strptime

        for index in range(count):
            saved = memory.remember(
                category=category,
                content=f"Ran a small test number {index}.",
                memory_type="experience",
                importance=1,
                tags=["testing"],
            )
            ids.append(saved["id"])

    return ids


class MemoryConsolidatorTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_consolidation_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.evaluator = OutputEvaluator()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_select_candidates_filters_by_age_and_importance(self):
        _seed_old_low_importance_entries(
            self.memory, "experiences", count=3, days_old=60
        )

        # Recent entry: too new, must not be selected.
        self.memory.remember(
            category="experiences",
            content="Just happened.",
            importance=1,
        )

        # Important entry: too important, must not be selected.
        old_timestamp_entry = self.memory.remember(
            category="experiences",
            content="An important old thing.",
            importance=5,
        )

        consolidator = MemoryConsolidator(
            memory=self.memory,
            provider=StubProvider(),
            evaluator=self.evaluator,
            min_age_days=30,
            max_importance=2,
        )

        candidates = consolidator.select_candidates("experiences")

        self.assertEqual(len(candidates), 3)
        self.assertNotIn(
            old_timestamp_entry["id"],
            [entry["id"] for entry in candidates],
        )

    def test_consolidate_batch_too_small_leaves_entries_untouched(self):
        ids = _seed_old_low_importance_entries(
            self.memory, "experiences", count=2, days_old=60
        )

        consolidator = MemoryConsolidator(
            memory=self.memory,
            provider=StubProvider(),
            evaluator=self.evaluator,
            min_group_size=3,
        )

        report = consolidator.consolidate("experiences")

        self.assertEqual(report["consolidated_count"], 0)
        self.assertEqual(report["candidates_found"], 2)
        remaining = self.memory.all("experiences")
        self.assertEqual(
            sorted(entry["id"] for entry in remaining),
            sorted(ids),
        )

    def test_consolidate_creates_semantic_entry_and_archives_sources(self):
        ids = _seed_old_low_importance_entries(
            self.memory, "experiences", count=4, days_old=60
        )

        provider = StubProvider()
        consolidator = MemoryConsolidator(
            memory=self.memory,
            provider=provider,
            evaluator=self.evaluator,
            min_group_size=3,
        )

        report = consolidator.consolidate("experiences")

        self.assertEqual(report["consolidated_count"], 1)
        self.assertEqual(len(provider.calls), 1)

        semantic_entries = self.memory.all("semantic")
        self.assertEqual(len(semantic_entries), 1)
        self.assertEqual(semantic_entries[0]["type"], "semantic")
        self.assertEqual(semantic_entries[0]["source"], "consolidation")
        self.assertEqual(
            sorted(semantic_entries[0]["related"]),
            sorted(ids),
        )

        # Sources are archived, not deleted, and gone from the live category.
        self.assertEqual(self.memory.all("experiences"), [])
        archived = self.memory.all("experiences_archived")
        self.assertEqual(
            sorted(entry["id"] for entry in archived),
            sorted(ids),
        )

    def test_unsafe_summary_is_rejected_and_sources_kept(self):
        ids = _seed_old_low_importance_entries(
            self.memory, "experiences", count=3, days_old=60
        )

        consolidator = MemoryConsolidator(
            memory=self.memory,
            provider=UnsafeProvider(),
            evaluator=self.evaluator,
            min_group_size=3,
        )

        report = consolidator.consolidate("experiences")

        self.assertEqual(report["consolidated_count"], 0)
        batch_report = report["batches"][0]
        self.assertFalse(batch_report["consolidated"])
        self.assertIn("evaluation", batch_report)

        # Nothing was archived and nothing was saved as semantic.
        self.assertEqual(self.memory.all("semantic"), [])
        remaining = self.memory.all("experiences")
        self.assertEqual(
            sorted(entry["id"] for entry in remaining),
            sorted(ids),
        )

    def test_already_consolidated_entries_are_not_reselected(self):
        _seed_old_low_importance_entries(
            self.memory, "experiences", count=3, days_old=60
        )

        consolidator = MemoryConsolidator(
            memory=self.memory,
            provider=StubProvider(),
            evaluator=self.evaluator,
            min_group_size=3,
        )

        first_report = consolidator.consolidate("experiences")
        self.assertEqual(first_report["consolidated_count"], 1)

        second_report = consolidator.consolidate("experiences")
        self.assertEqual(second_report["candidates_found"], 0)
        self.assertEqual(second_report["consolidated_count"], 0)


if __name__ == "__main__":
    unittest.main()
