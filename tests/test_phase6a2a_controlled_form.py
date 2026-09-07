"""Tests for Phase 6A.2A controlled FORM mutation."""

import tempfile
import unittest

from brain.belief_mutation import (
    ControlledBeliefMutator,
    safely_apply_belief_mutation,
)
from brain.beliefs import BeliefSystem
from brain.memory import MemoryEngine


class Phase6A2AControlledFormTests(
    unittest.TestCase
):

    def setUp(
        self,
    ):
        self.tempdir = (
            tempfile.TemporaryDirectory()
        )

        self.memory = MemoryEngine(
            root=self.tempdir.name
        )

        self.mutator = (
            ControlledBeliefMutator(
                self.memory
            )
        )

        evidence_entry = (
            self.memory.remember(
                category="research_evidence",
                content=(
                    "A traceable human source "
                    "reported a practical observation."
                ),
                memory_type="observation",
                source="test-source",
                importance=3,
                tags=[
                    "test",
                    "qualified",
                ],
                related=[],
            )
        )

        self.evidence_id = (
            evidence_entry["id"]
        )

        self.evidence = [{
            "memory_id": (
                self.evidence_id
            ),
            "title": "Test Source",
            "url": (
                "https://example.com/source"
            ),
            "observation": (
                "A traceable practical observation."
            ),
        }]

    def tearDown(
        self,
    ):
        self.tempdir.cleanup()

    def proposal(
        self,
        **overrides,
    ):
        value = {
            "stage": "proposed",
            "action": "form",
            "relation": "form",
            "candidate_statement": (
                "Practical experience can "
                "contribute knowledge that is "
                "difficult to express as facts alone."
            ),
            "related_belief_id": None,
            "proposed_confidence": 0.72,
            "reason": (
                "Qualified evidence supports "
                "forming a provisional belief."
            ),
            "evidence_ids": [
                self.evidence_id
            ],
        }

        value.update(
            overrides
        )

        return value

    def active_beliefs(
        self,
    ):
        return (
            BeliefSystem(
                self.memory
            ).active_beliefs()
        )

    def test_missing_proposal_is_blocked(
        self,
    ):
        result = (
            self.mutator.apply(
                None,
                self.evidence,
            )
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            result["stage"],
            "mutation-blocked",
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_only_proposed_stage_can_mutate(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                stage="integration-error"
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_support_requires_review_existing_action(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                action="support",
                relation="support",
                related_belief_id=(
                    "belief-123"
                ),
            ),
            self.evidence,
        )

        self.assertEqual(
            result["stage"],
            "mutation-blocked",
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_form_relation_must_match_action(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                relation="mixed"
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_form_cannot_target_existing_belief(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                related_belief_id=(
                    "existing-belief"
                )
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_missing_qualified_evidence_blocks_form(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(),
            [],
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_unknown_evidence_id_blocks_form(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                evidence_ids=[
                    "unknown-evidence"
                ]
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_candidate_statement_is_required(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                candidate_statement="   "
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_confidence_must_be_numeric_and_bounded(
        self,
    ):
        invalid_values = [
            True,
            "0.7",
            -0.01,
            1.01,
        ]

        for value in invalid_values:
            with self.subTest(
                confidence=value
            ):
                result = (
                    self.mutator.apply(
                        self.proposal(
                            proposed_confidence=(
                                value
                            )
                        ),
                        self.evidence,
                    )
                )

                self.assertFalse(
                    result["applied"]
                )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_reason_is_required(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(
                reason=""
            ),
            self.evidence,
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            self.active_beliefs(),
            [],
        )

    def test_valid_form_persists_real_belief(
        self,
    ):
        result = self.mutator.apply(
            self.proposal(),
            self.evidence,
        )

        self.assertTrue(
            result["applied"]
        )

        self.assertEqual(
            result["stage"],
            "mutation-applied",
        )

        self.assertEqual(
            result["action"],
            "form",
        )

        self.assertEqual(
            result["relation"],
            "form",
        )

        self.assertEqual(
            result["evidence_ids"],
            [
                self.evidence_id
            ],
        )

        beliefs = (
            self.active_beliefs()
        )

        self.assertEqual(
            len(beliefs),
            1,
        )

        self.assertEqual(
            beliefs[0]["statement"],
            self.proposal()[
                "candidate_statement"
            ],
        )

        self.assertAlmostEqual(
            beliefs[0]["confidence"],
            0.72,
        )

        self.assertIsNotNone(
            result["audit_entry"]
        )

    def test_exact_replay_is_suppressed(
        self,
    ):
        first = self.mutator.apply(
            self.proposal(),
            self.evidence,
        )

        self.assertTrue(
            first["applied"]
        )

        second = self.mutator.apply(
            self.proposal(),
            self.evidence,
        )

        self.assertFalse(
            second["applied"]
        )

        self.assertEqual(
            second["stage"],
            "duplicate-suppressed",
        )

        self.assertEqual(
            len(
                self.active_beliefs()
            ),
            1,
        )

    def test_safe_wrapper_preserves_no_mutation_on_invalid_input(
        self,
    ):
        before = (
            self.active_beliefs()
        )

        result = (
            safely_apply_belief_mutation(
                memory=self.memory,
                proposal={
                    "stage": "proposed",
                    "action": (
                        "contradict"
                    ),
                    "relation": (
                        "contradict"
                    ),
                },
                qualified_evidence=(
                    self.evidence
                ),
            )
        )

        after = (
            self.active_beliefs()
        )

        self.assertFalse(
            result["applied"]
        )

        self.assertEqual(
            before,
            after,
        )


if __name__ == "__main__":
    unittest.main()
