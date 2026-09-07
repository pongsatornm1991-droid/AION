
import ast
import tempfile
import unittest
from pathlib import Path

from brain.bounded_tracker import BoundedItemTracker
from brain.memory import MemoryEngine


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "brain" / "learning.py"
TRACKER = ROOT / "brain" / "bounded_tracker.py"


class DemoTracker(BoundedItemTracker):
    CATEGORY = "phase5f5k_items"
    MEMORY_TYPE = "question"
    ITEM_LABEL = "Question"
    RESOLUTION_LABEL = "Answer"
    DEFAULT_BUDGET = 3


class Phase5F5KTests(unittest.TestCase):

    def test_01_record_attempt_refuses_when_budget_exhausted(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = MemoryEngine(root=temp)
            tracker = DemoTracker(memory)

            opened = tracker.open_item(
                statement="test",
                completion_criteria="done",
                budget=1,
            )

            first = tracker.record_attempt(
                opened["id"],
                note="first",
            )

            with self.assertRaises(ValueError):
                tracker.record_attempt(
                    first["id"],
                    note="must not become 2/1",
                )

    def test_02_resolve_is_still_allowed_at_budget_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = MemoryEngine(root=temp)
            tracker = DemoTracker(memory)

            opened = tracker.open_item(
                statement="test",
                completion_criteria="done",
                budget=1,
            )

            exhausted = tracker.record_attempt(
                opened["id"],
                note="used budget",
            )

            resolved = tracker.resolve_item(
                exhausted["id"],
                resolution="complete",
                evidence=[
                    {
                        "description": "traceable evidence",
                        "id": "evidence123",
                    }
                ],
            )

            history = tracker.history(
                resolved["id"]
            )

            self.assertEqual(
                history[-1]["attempts"],
                1,
            )
            self.assertEqual(
                tracker.status_of(
                    tracker._get(resolved["id"])
                ),
                "resolved",
            )

    def test_03_learning_has_phase_marker(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "PHASE 5F.5K — EVIDENCE-READY COMPLETION RETRY",
            source,
        )

    def test_04_tracker_has_hard_budget_marker(self):
        source = TRACKER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "PHASE 5F.5K — HARD ATTEMPT BUDGET",
            source,
        )

    def test_05_exhausted_missing_evidence_stops_before_retrieval(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        budget_pos = source.index(
            '"stage": "budget-exhausted"'
        )
        retrieval_pos = source.index(
            "self._retrieve_from_adapter(",
            budget_pos,
        )

        self.assertLess(
            budget_pos,
            retrieval_pos,
        )

    def test_06_resume_path_is_preserved(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "resume_from_existing_evidence",
            source,
        )
        self.assertIn(
            '"stage": (\n'
            '                    "existing-evidence-ready"',
            source,
        )

    def test_07_criteria_scoped_synthesis_is_preserved(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "completion_criteria=(",
            source,
        )
        self.assertIn(
            ".synthesize_answer(",
            source,
        )

    def test_08_budget_exhausted_completion_failure_skips_attempt(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        no_attempt = source.index(
            "PHASE 5F.5K — NO ATTEMPT N+1 "
            "AFTER EVIDENCE RETRY"
        )
        record_attempt = source.index(
            ".record_attempt(",
            no_attempt,
        )

        self.assertLess(
            no_attempt,
            record_attempt,
        )

        between = source[
            no_attempt:record_attempt
        ]

        self.assertIn(
            "if budget_exhausted:",
            between,
        )
        self.assertIn(
            '"completion_retry": True',
            between,
        )
        self.assertIn(
            "return {",
            between,
        )

    def test_09_completion_path_still_calls_answer_question(self):
        source = LEARNING.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".answer_question(",
            source,
        )

    def test_10_tracker_guard_precedes_increment(self):
        source = TRACKER.read_text(
            encoding="utf-8"
        )

        guard = source.index(
            'if parsed["attempts"] >= parsed["budget"]:'
        )
        increment = source.index(
            'attempts=parsed["attempts"] + 1'
        )

        self.assertLess(
            guard,
            increment,
        )

    def test_11_files_parse_after_patch(self):
        ast.parse(
            LEARNING.read_text(
                encoding="utf-8"
            )
        )
        ast.parse(
            TRACKER.read_text(
                encoding="utf-8"
            )
        )


if __name__ == "__main__":
    unittest.main()
