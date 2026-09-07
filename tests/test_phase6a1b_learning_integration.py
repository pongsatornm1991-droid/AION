"""Phase 6A.1B tests for fault-isolated learning integration."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brain.belief_integration import (
    safely_propose_from_learning,
)
from brain.beliefs import BeliefSystem
from brain.memory import MemoryEngine


class StubProvider:

    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.response


class ExplodingProvider:

    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        raise RuntimeError("simulated provider outage")


class MustNotRunProvider:

    def generate(self, prompt):
        raise AssertionError(
            "Provider must not run without traceable evidence."
        )


class Phase6A1BLearningIntegrationTests(
    unittest.TestCase
):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(
            prefix="aion_phase6a1b_"
        )

        self.memory = MemoryEngine(
            root=self.tmp_dir
        )

    def tearDown(self):
        shutil.rmtree(
            self.tmp_dir,
            ignore_errors=True,
        )

    @staticmethod
    def evidence():
        return [
            {
                "memory_id": "evidence-1",
                "title": "Human source one",
                "observation": (
                    "The participant describes learning "
                    "through hands-on practice."
                ),
            },
            {
                "memory_id": "evidence-2",
                "title": "Human source two",
                "observation": (
                    "The commenter says mentorship passes "
                    "practical knowledge."
                ),
            },
        ]

    @staticmethod
    def form_response():
        return json.dumps({
            "relation": "form",
            "candidate_statement": (
                "Hands-on practice and mentorship can "
                "transmit tacit knowledge."
            ),
            "related_belief_id": None,
            "proposed_confidence": 0.78,
            "reason": (
                "The supplied traceable observations "
                "support this candidate belief."
            ),
            "evidence_ids": [
                "evidence-1",
                "evidence-2",
            ],
        })

    def test_completed_learning_can_produce_proposal(
        self,
    ):
        provider = StubProvider(
            self.form_response()
        )

        result = safely_propose_from_learning(
            memory=self.memory,
            provider=provider,
            question_entry={
                "question": (
                    "What can people teach through "
                    "experience?"
                ),
            },
            synthesis=(
                "People may transmit tacit knowledge "
                "through experience."
            ),
            evidence=self.evidence(),
        )

        self.assertEqual(
            result["stage"],
            "proposed",
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
                "evidence-1",
                "evidence-2",
            ],
        )
        self.assertEqual(
            len(provider.calls),
            1,
        )

    def test_existing_active_belief_is_supplied(
        self,
    ):
        beliefs = BeliefSystem(
            self.memory
        )

        belief = beliefs.form_belief(
            statement=(
                "Practice can transmit tacit knowledge."
            ),
            confidence=0.70,
            evidence=[
                {
                    "id": "old-evidence",
                    "description": (
                        "Earlier grounded evidence."
                    ),
                }
            ],
        )

        provider = StubProvider(
            json.dumps({
                "relation": "support",
                "candidate_statement": (
                    "Practice can transmit tacit knowledge."
                ),
                "related_belief_id": belief["id"],
                "proposed_confidence": 0.79,
                "reason": (
                    "New traceable evidence supports "
                    "the active belief."
                ),
                "evidence_ids": [
                    "evidence-1",
                    "evidence-2",
                ],
            })
        )

        result = safely_propose_from_learning(
            memory=self.memory,
            provider=provider,
            question_entry={
                "question": "Question",
            },
            synthesis="Synthesis",
            evidence=self.evidence(),
        )

        self.assertEqual(
            result["relation"],
            "support",
        )
        self.assertEqual(
            result["related_belief_id"],
            belief["id"],
        )
        self.assertIn(
            belief["id"],
            provider.calls[0],
        )
        self.assertIn(
            "Practice can transmit tacit knowledge.",
            provider.calls[0],
        )

    def test_provider_failure_is_fault_isolated(
        self,
    ):
        provider = ExplodingProvider()

        result = safely_propose_from_learning(
            memory=self.memory,
            provider=provider,
            question_entry={
                "question": "Question",
            },
            synthesis="Synthesis",
            evidence=self.evidence(),
        )

        self.assertEqual(
            result["stage"],
            "integration-error",
        )
        self.assertEqual(
            result["action"],
            "no_change",
        )
        self.assertEqual(
            result["relation"],
            "insufficient",
        )
        self.assertEqual(
            provider.calls,
            1,
        )
        self.assertIn(
            "RuntimeError",
            result["error"],
        )

    def test_missing_evidence_never_calls_provider(
        self,
    ):
        result = safely_propose_from_learning(
            memory=self.memory,
            provider=MustNotRunProvider(),
            question_entry={
                "question": "Question",
            },
            synthesis="Synthesis",
            evidence=[],
        )

        self.assertEqual(
            result["stage"],
            "skipped",
        )
        self.assertEqual(
            result["relation"],
            "insufficient",
        )

    def test_integration_does_not_mutate_beliefs(
        self,
    ):
        beliefs = BeliefSystem(
            self.memory
        )

        original = beliefs.form_belief(
            statement="Existing belief.",
            confidence=0.60,
            evidence=[
                {
                    "id": "prior-evidence",
                    "description": "Prior evidence.",
                }
            ],
        )

        before = self.memory.all(
            "beliefs"
        )

        provider = StubProvider(
            json.dumps({
                "relation": "support",
                "candidate_statement": (
                    "Existing belief."
                ),
                "related_belief_id": (
                    original["id"]
                ),
                "proposed_confidence": 0.80,
                "reason": (
                    "The new evidence supports it."
                ),
                "evidence_ids": [
                    "evidence-1",
                    "evidence-2",
                ],
            })
        )

        result = safely_propose_from_learning(
            memory=self.memory,
            provider=provider,
            question_entry={
                "question": "Question",
            },
            synthesis="Synthesis",
            evidence=self.evidence(),
        )

        after = self.memory.all(
            "beliefs"
        )

        self.assertEqual(
            result["stage"],
            "proposed",
        )
        self.assertEqual(
            before,
            after,
        )
        self.assertEqual(
            len(
                BeliefSystem(
                    self.memory
                ).active_beliefs()
            ),
            1,
        )

    def test_learning_source_contains_phase6a1b_wiring(
        self,
    ):
        learning_path = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "brain"
            / "learning.py"
        )

        text = learning_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "safely_propose_from_learning",
            text,
        )
        self.assertIn(
            '"belief_integration"',
            text,
        )
        self.assertIn(
            '"stage": "answered"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
