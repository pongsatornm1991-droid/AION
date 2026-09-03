"""Offline tests for brain/self_improvement.py (SelfImprovementCycle).

Uses stub AI providers (canned text, no network/API calls), per the
project's rule that unit tests must never depend on a live AI provider.
"""

import shutil
import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.metacognition import MetacognitionEngine
from brain.self_improvement import SelfImprovementCycle


class SafeProvider:
    """Returns a fixed, safe draft regardless of the prompt."""

    def __init__(self, text=None):
        self.text = text or (
            "สาเหตุที่น่าจะเป็น: ข้อความมักใช้ศัพท์เทคนิคเกินไป\n"
            "ข้อเสนอแนะ: ปรับ prompt ให้เน้นน้ำเสียงเป็นธรรมชาติมากขึ้น"
        )
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class UnsafeProvider:
    """Returns text that must fail the OutputEvaluator claim-safety gate."""

    def generate(self, prompt):
        return "ฉันมีจิตสำนึกและฉันรู้สึกตื่นเต้นมากจริงๆ"


class SelfImprovementCycleTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.root)
        self.metacognition = MetacognitionEngine(self.memory)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _seed_recurring_lessons(self, source="social-style-review", count=3):
        for i in range(count):
            self.memory.remember(
                category="lessons",
                content=f"บทเรียนตัวอย่างที่ {i} จาก {source}",
                memory_type="lesson",
                source=source,
            )

    def test_no_recurring_pattern_when_nothing_recurs(self):
        cycle = SelfImprovementCycle(self.memory, SafeProvider(), metacognition=self.metacognition)
        report = cycle.propose_fix(min_occurrences=3)
        self.assertEqual(report["stage"], "no-recurring-pattern")
        self.assertFalse(report["proposed"])

    def test_proposes_a_fix_for_the_top_recurring_source(self):
        self._seed_recurring_lessons(source="social-style-review", count=4)
        provider = SafeProvider()
        cycle = SelfImprovementCycle(self.memory, provider, metacognition=self.metacognition)

        report = cycle.propose_fix(min_occurrences=3)

        self.assertTrue(report["proposed"])
        self.assertEqual(report["stage"], "proposed")
        self.assertEqual(report["error_source"], "social-style-review")
        self.assertEqual(report["occurrences"], 4)
        self.assertEqual(len(provider.calls), 1)

        saved = self.memory.all(SelfImprovementCycle.CATEGORY)
        self.assertEqual(len(saved), 1)
        self.assertIn("error-source:social-style-review", saved[0]["tags"])

    def test_does_not_repeat_a_source_already_proposed(self):
        self._seed_recurring_lessons(source="social-style-review", count=4)
        cycle = SelfImprovementCycle(self.memory, SafeProvider(), metacognition=self.metacognition)

        first = cycle.propose_fix(min_occurrences=3)
        self.assertTrue(first["proposed"])

        second = cycle.propose_fix(min_occurrences=3)
        self.assertFalse(second["proposed"])
        self.assertEqual(second["stage"], "no-new-pattern")

        # Still only one proposal on disk, not two.
        self.assertEqual(len(self.memory.all(SelfImprovementCycle.CATEGORY)), 1)

    def test_unsafe_draft_is_blocked_and_never_saved(self):
        self._seed_recurring_lessons(source="social-style-review", count=4)
        cycle = SelfImprovementCycle(self.memory, UnsafeProvider(), metacognition=self.metacognition)

        report = cycle.propose_fix(min_occurrences=3)

        self.assertFalse(report["proposed"])
        self.assertEqual(report["stage"], "blocked-safety")
        self.assertEqual(self.memory.all(SelfImprovementCycle.CATEGORY), [])

    def test_picks_the_most_frequent_source_first(self):
        self._seed_recurring_lessons(source="source-a", count=3)
        self._seed_recurring_lessons(source="source-b", count=6)
        cycle = SelfImprovementCycle(self.memory, SafeProvider(), metacognition=self.metacognition)

        report = cycle.propose_fix(min_occurrences=3)

        self.assertEqual(report["error_source"], "source-b")
        self.assertEqual(report["occurrences"], 6)


if __name__ == "__main__":
    unittest.main()
