"""Tests for Phase 6A.3 controlled SUPPORT revision."""

import tempfile
import unittest
from unittest.mock import patch

from brain.belief_mutation import (
    ControlledBeliefMutator,
    safely_apply_belief_mutation,
)
from brain.beliefs import BeliefSystem
from brain.memory import MemoryEngine


class Phase6A3AControlledSupportTests(unittest.TestCase):
    STATEMENT = (
        "Practical experience can contribute knowledge that facts "
        "alone do not fully express."
    )

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = MemoryEngine(root=self.tempdir.name)
        self.beliefs = BeliefSystem(self.memory)
        self.mutator = ControlledBeliefMutator(self.memory)

        original = self._remember_evidence("Original Source")
        new = self._remember_evidence("New Supporting Source")
        extra = self._remember_evidence("Additional Supporting Source")

        self.original_id = original["memory_id"]
        self.new_id = new["memory_id"]
        self.extra_id = extra["memory_id"]
        self.original_evidence = original
        self.new_evidence = new
        self.extra_evidence = extra

        self.initial = self.beliefs.form_belief(
            statement=self.STATEMENT,
            confidence=0.60,
            evidence=[{
                "id": self.original_id,
                "description": "Original Source",
            }],
            tags=["test", "evidence-grounded"],
            source="test-form",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _remember_evidence(self, title):
        entry = self.memory.remember(
            category="research_evidence",
            content=f"{title} reports a traceable observation.",
            memory_type="observation",
            source="test-source",
            importance=3,
            tags=["test", "qualified"],
            related=[],
        )
        return {
            "memory_id": entry["id"],
            "title": title,
            "url": "https://example.com/evidence",
            "observation": "A traceable supporting observation.",
        }

    def proposal(self, **overrides):
        value = {
            "stage": "proposed",
            "action": "review_existing",
            "relation": "support",
            "candidate_statement": self.STATEMENT,
            "related_belief_id": self.initial["id"],
            "proposed_confidence": 0.78,
            "reason": "New qualified evidence strengthens the belief.",
            "evidence_ids": [self.new_id],
        }
        value.update(overrides)
        return value

    def test_valid_support_creates_immutable_revision_and_audit(self):
        result = self.mutator.apply(
            self.proposal(),
            [self.new_evidence],
        )

        self.assertTrue(result["applied"])
        self.assertEqual(result["stage"], "mutation-applied")
        self.assertEqual(result["action"], "support")
        self.assertEqual(result["relation"], "support")
        self.assertEqual(result["predecessor_id"], self.initial["id"])
        self.assertEqual(result["evidence_ids"], [self.new_id])

        active = self.beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["statement"], self.STATEMENT)
        self.assertAlmostEqual(active[0]["confidence"], 0.78)
        self.assertEqual(active[0]["predecessor"], self.initial["id"])

        evidence_ids = {
            item.get("id")
            for item in active[0]["evidence"]
            if isinstance(item, dict)
        }
        self.assertIn(self.original_id, evidence_ids)
        self.assertIn(self.new_id, evidence_ids)

        history = self.beliefs.history(active[0]["id"])
        self.assertEqual(len(history), 2)
        self.assertEqual(
            self.beliefs.status_of(history[0]),
            "superseded",
        )
        self.assertIsNotNone(result["audit_entry"])
        self.assertIn(
            "Action: SUPPORT",
            result["audit_entry"]["content"],
        )

    def test_support_target_must_exist_and_be_active(self):
        missing = self.mutator.apply(
            self.proposal(related_belief_id="missing"),
            [self.new_evidence],
        )
        self.assertFalse(missing["applied"])

        first = self.mutator.apply(
            self.proposal(),
            [self.new_evidence],
        )
        self.assertTrue(first["applied"])

        stale = self.mutator.apply(
            self.proposal(evidence_ids=[self.extra_id]),
            [self.extra_evidence],
        )
        self.assertEqual(stale["stage"], "mutation-blocked")
        self.assertFalse(stale["applied"])

    def test_support_cannot_change_statement(self):
        result = self.mutator.apply(
            self.proposal(candidate_statement="A different claim."),
            [self.new_evidence],
        )
        self.assertEqual(result["stage"], "mutation-blocked")
        self.assertEqual(len(self.beliefs.active_beliefs()), 1)

    def test_support_cannot_lower_confidence(self):
        result = self.mutator.apply(
            self.proposal(proposed_confidence=0.59),
            [self.new_evidence],
        )
        self.assertEqual(result["stage"], "mutation-blocked")
        self.assertEqual(len(self.beliefs.history(self.initial["id"])), 1)

    def test_equal_confidence_is_allowed_with_new_evidence(self):
        result = self.mutator.apply(
            self.proposal(proposed_confidence=0.60),
            [self.new_evidence],
        )
        self.assertTrue(result["applied"])

    def test_support_confidence_must_be_numeric_and_bounded(self):
        for value in (True, "0.8", -0.01, 1.01):
            with self.subTest(value=value):
                result = self.mutator.apply(
                    self.proposal(proposed_confidence=value),
                    [self.new_evidence],
                )
                self.assertFalse(result["applied"])

    def test_support_requires_explicit_rationale(self):
        result = self.mutator.apply(
            self.proposal(reason="  "),
            [self.new_evidence],
        )
        self.assertFalse(result["applied"])

    def test_support_requires_qualified_persisted_evidence(self):
        no_evidence = self.mutator.apply(self.proposal(), [])
        self.assertFalse(no_evidence["applied"])

        unknown = self.mutator.apply(
            self.proposal(evidence_ids=["unknown"]),
            [self.new_evidence],
        )
        self.assertFalse(unknown["applied"])

    def test_replayed_evidence_is_suppressed_on_current_revision(self):
        first = self.mutator.apply(
            self.proposal(),
            [self.new_evidence],
        )
        current = self.beliefs.active_beliefs()[0]
        audit_count = len(self.memory.all("belief_mutations"))

        replay = self.mutator.apply(
            self.proposal(
                related_belief_id=current["id"],
                proposed_confidence=0.82,
            ),
            [self.new_evidence],
        )

        self.assertTrue(first["applied"])
        self.assertFalse(replay["applied"])
        self.assertEqual(replay["stage"], "duplicate-suppressed")
        self.assertEqual(len(self.beliefs.active_beliefs()), 1)
        self.assertEqual(
            len(self.memory.all("belief_mutations")),
            audit_count,
        )

    def test_only_new_ids_are_added_when_proposal_mixes_old_and_new(self):
        result = self.mutator.apply(
            self.proposal(evidence_ids=[self.original_id, self.new_id]),
            [self.original_evidence, self.new_evidence],
        )
        self.assertTrue(result["applied"])
        self.assertEqual(result["evidence_ids"], [self.new_id])

    def test_contradict_mixed_and_retract_remain_disabled(self):
        cases = (
            ("review_existing", "contradict"),
            ("review_existing", "mixed"),
            ("retract", "retract"),
        )
        for action, relation in cases:
            with self.subTest(relation=relation):
                result = self.mutator.apply(
                    self.proposal(action=action, relation=relation),
                    [self.new_evidence],
                )
                self.assertFalse(result["applied"])

    def test_revision_failure_is_fault_isolated(self):
        with patch.object(
            self.mutator.beliefs,
            "revise_belief",
            side_effect=RuntimeError("test failure"),
        ):
            result = self.mutator.apply(
                self.proposal(),
                [self.new_evidence],
            )

        self.assertEqual(result["stage"], "mutation-error")
        self.assertFalse(result["applied"])
        self.assertEqual(len(self.beliefs.active_beliefs()), 1)

    def test_audit_failure_does_not_undo_successful_revision(self):
        with patch.object(
            self.mutator,
            "_write_support_audit",
            side_effect=RuntimeError("test audit failure"),
        ):
            result = self.mutator.apply(
                self.proposal(),
                [self.new_evidence],
            )

        self.assertEqual(result["stage"], "applied-with-audit-error")
        self.assertTrue(result["applied"])
        self.assertEqual(len(self.beliefs.active_beliefs()), 1)
        self.assertNotEqual(
            self.beliefs.active_beliefs()[0]["id"],
            self.initial["id"],
        )

    def test_safe_wrapper_applies_valid_support(self):
        result = safely_apply_belief_mutation(
            memory=self.memory,
            proposal=self.proposal(),
            qualified_evidence=[self.new_evidence],
        )
        self.assertTrue(result["applied"])
        self.assertEqual(result["relation"], "support")


if __name__ == "__main__":
    unittest.main()
