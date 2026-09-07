"""Deterministic tests for Phase 6A.1 belief integration proposals."""

import json
import unittest

from brain.belief_integration import BeliefIntegrationEvaluator


class StubProvider:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.response


class ExplodingProvider:
    def generate(self, prompt):
        raise AssertionError(
            "Provider must not be called when evidence is absent."
        )


class BeliefIntegrationEvaluatorTests(unittest.TestCase):

    def evidence(self):
        return [
            {
                "memory_id": "ev-1",
                "title": "Source One",
                "observation": "A traceable observation.",
            },
            {
                "memory_id": "ev-2",
                "title": "Source Two",
                "observation": "Another traceable observation.",
            },
        ]

    def belief(self):
        return [{
            "id": "belief-1",
            "statement": "Practice can transmit tacit knowledge.",
            "confidence": 0.70,
        }]

    def response(self, **overrides):
        payload = {
            "relation": "form",
            "candidate_statement": (
                "Hands-on practice can transmit tacit knowledge."
            ),
            "related_belief_id": None,
            "proposed_confidence": 0.76,
            "reason": (
                "The supplied observations support the candidate claim."
            ),
            "evidence_ids": ["ev-1", "ev-2"],
        }
        payload.update(overrides)
        return json.dumps(payload)

    def test_missing_evidence_skips_without_provider(self):
        evaluator = BeliefIntegrationEvaluator(
            ExplodingProvider()
        )

        result = evaluator.propose(
            question="What can people teach through experience?",
            synthesis="A synthesis.",
            evidence=[],
            active_beliefs=[],
        )

        self.assertEqual(result["stage"], "skipped")
        self.assertEqual(result["action"], "no_change")
        self.assertEqual(result["relation"], "insufficient")

    def test_form_proposal_uses_real_evidence_ids(self):
        provider = StubProvider(self.response())
        evaluator = BeliefIntegrationEvaluator(provider)

        result = evaluator.propose(
            question="What can people teach through experience?",
            synthesis="A synthesis.",
            evidence=self.evidence(),
            active_beliefs=[],
        )

        self.assertEqual(result["stage"], "proposed")
        self.assertEqual(result["action"], "form")
        self.assertEqual(result["relation"], "form")
        self.assertEqual(result["evidence_ids"], ["ev-1", "ev-2"])
        self.assertEqual(len(provider.calls), 1)

    def test_unknown_evidence_id_is_rejected(self):
        provider = StubProvider(
            self.response(evidence_ids=["invented-id"])
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )

    def test_support_requires_existing_active_belief(self):
        provider = StubProvider(
            self.response(
                relation="support",
                related_belief_id="belief-1",
                proposed_confidence=0.82,
            )
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        result = evaluator.propose(
            question="Question",
            synthesis="Synthesis",
            evidence=self.evidence(),
            active_beliefs=self.belief(),
        )

        self.assertEqual(result["action"], "review_existing")
        self.assertEqual(result["relation"], "support")
        self.assertEqual(
            result["related_belief_id"],
            "belief-1",
        )

    def test_support_rejects_unknown_belief(self):
        provider = StubProvider(
            self.response(
                relation="support",
                related_belief_id="not-real",
            )
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=self.belief(),
            )

    def test_form_rejects_existing_belief_target(self):
        provider = StubProvider(
            self.response(
                relation="form",
                related_belief_id="belief-1",
            )
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=self.belief(),
            )

    def test_insufficient_means_no_change(self):
        provider = StubProvider(
            self.response(
                relation="insufficient",
                candidate_statement=None,
                related_belief_id=None,
                proposed_confidence=None,
                evidence_ids=["ev-1"],
            )
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        result = evaluator.propose(
            question="Question",
            synthesis="Synthesis",
            evidence=self.evidence(),
            active_beliefs=self.belief(),
        )

        self.assertEqual(result["action"], "no_change")
        self.assertEqual(result["relation"], "insufficient")
        self.assertIsNone(result["proposed_confidence"])

    def test_unrelated_means_no_change(self):
        provider = StubProvider(
            self.response(
                relation="unrelated",
                candidate_statement=None,
                related_belief_id=None,
                proposed_confidence=None,
                evidence_ids=[],
            )
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        result = evaluator.propose(
            question="Question",
            synthesis="Synthesis",
            evidence=self.evidence(),
            active_beliefs=self.belief(),
        )

        self.assertEqual(result["action"], "no_change")
        self.assertEqual(result["relation"], "unrelated")

    def test_actionable_proposal_requires_candidate_statement(self):
        provider = StubProvider(
            self.response(candidate_statement=None)
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )

    def test_actionable_proposal_requires_numeric_confidence(self):
        provider = StubProvider(
            self.response(proposed_confidence="high")
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )

    def test_confidence_out_of_range_is_rejected(self):
        provider = StubProvider(
            self.response(proposed_confidence=1.4)
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )

    def test_reason_is_required(self):
        provider = StubProvider(
            self.response(reason="   ")
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )

    def test_provider_cannot_mutate_beliefs(self):
        provider = StubProvider(self.response())
        evaluator = BeliefIntegrationEvaluator(provider)

        active = self.belief()
        before = json.dumps(active, sort_keys=True)

        evaluator.propose(
            question="Question",
            synthesis="Synthesis",
            evidence=self.evidence(),
            active_beliefs=active,
        )

        after = json.dumps(active, sort_keys=True)
        self.assertEqual(before, after)

    def test_synthesis_is_context_not_evidence(self):
        provider = StubProvider(self.response())
        evaluator = BeliefIntegrationEvaluator(provider)

        evaluator.propose(
            question="Question",
            synthesis="UNIQUE_SYNTHESIS_CONTEXT",
            evidence=self.evidence(),
            active_beliefs=[],
        )

        prompt = provider.calls[0]

        self.assertIn(
            "The synthesis is context, not evidence by itself.",
            prompt,
        )
        self.assertIn(
            "UNIQUE_SYNTHESIS_CONTEXT",
            prompt,
        )

    def test_markdown_fenced_json_is_accepted(self):
        provider = StubProvider(
            "```json\n" + self.response() + "\n```"
        )
        evaluator = BeliefIntegrationEvaluator(provider)

        result = evaluator.propose(
            question="Question",
            synthesis="Synthesis",
            evidence=self.evidence(),
            active_beliefs=[],
        )

        self.assertEqual(result["relation"], "form")

    def test_invalid_json_is_rejected(self):
        evaluator = BeliefIntegrationEvaluator(
            StubProvider("not json")
        )

        with self.assertRaises(ValueError):
            evaluator.propose(
                question="Question",
                synthesis="Synthesis",
                evidence=self.evidence(),
                active_beliefs=[],
            )


if __name__ == "__main__":
    unittest.main()
