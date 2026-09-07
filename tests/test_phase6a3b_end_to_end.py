"""Phase 6A.3 SUPPORT end-to-end verification with temporary memory."""

import json

from brain.beliefs import BeliefSystem
from brain.learning import WebLearningCycle, WebLearningGenerator
from tests.test_learning import (
    BaseLearningTest,
    FallbackSourceRegistry,
    SafeProvider,
    fake_fetch,
    fake_search,
)


class SupportAwareSafeProvider(SafeProvider):
    BELIEF_PROMPT_MARKER = (
        "You are AION's evidence-to-belief proposal evaluator."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.belief_prompts = []

    @staticmethod
    def _proposal_from_prompt(prompt):
        evidence_text = (
            prompt.split("QUALIFIED EVIDENCE:\n", 1)[1]
            .split("\n\nACTIVE BELIEFS:", 1)[0]
            .strip()
        )
        beliefs_text = (
            prompt.split("\n\nACTIVE BELIEFS:", 1)[1]
            .strip()
        )
        evidence = json.loads(evidence_text)
        beliefs = json.loads(beliefs_text)

        if not evidence or not beliefs:
            raise AssertionError(
                "SUPPORT end-to-end proposal requires evidence and a belief."
            )

        target = beliefs[0]
        evidence_ids = [
            item["id"]
            for item in evidence
            if isinstance(item, dict) and item.get("id")
        ]

        return json.dumps({
            "relation": "support",
            "candidate_statement": target["statement"],
            "related_belief_id": target["id"],
            "proposed_confidence": 0.82,
            "reason": (
                "The completed learning cycle supplied new qualified "
                "evidence supporting the active belief."
            ),
            "evidence_ids": evidence_ids,
        })

    def generate(self, prompt):
        if self.BELIEF_PROMPT_MARKER in prompt:
            self.belief_prompts.append(prompt)
            return self._proposal_from_prompt(prompt)
        return super().generate(prompt)


class Phase6A3BEndToEndTests(BaseLearningTest):
    STATEMENT = (
        "External observations can strengthen an existing provisional "
        "belief when their evidence remains traceable."
    )

    def _form_initial_belief(self):
        evidence = self.memory.remember(
            category="research_evidence",
            content="An earlier traceable source supplied initial support.",
            memory_type="observation",
            source="test-source",
            importance=3,
            tags=["test", "qualified"],
            related=[],
        )
        return BeliefSystem(self.memory).form_belief(
            statement=self.STATEMENT,
            confidence=0.64,
            evidence=[{
                "id": evidence["id"],
                "description": "Earlier traceable source",
            }],
            tags=["test", "evidence-grounded"],
            source="test-form",
        )

    def _build_cycle(self):
        self._raise_question()
        provider = SupportAwareSafeProvider(criteria_satisfied=True)
        cycle = WebLearningCycle(
            self.memory,
            self.curiosity,
            WebLearningGenerator(provider),
            search_fn=fake_search([]),
            fetch_fn=fake_fetch({}),
            source_registry=FallbackSourceRegistry(),
            fallback_search_fn=fake_search(["2301.12345"]),
            fallback_fetch_fn=fake_fetch({
                "2301.12345": {
                    "title": "A Paper About Plants",
                    "url": "https://arxiv.org/abs/2301.12345",
                    "extract": "This paper studies plant pigments.",
                }
            }),
        )
        return cycle, provider

    def test_learning_cycle_revises_active_belief_with_real_evidence(self):
        initial = self._form_initial_belief()
        cycle, provider = self._build_cycle()

        report = cycle.research_once()

        self.assertTrue(report["researched"])
        self.assertEqual(report["stage"], "answered")

        proposal = report["belief_integration"]
        self.assertEqual(proposal["stage"], "proposed")
        self.assertEqual(proposal["action"], "review_existing")
        self.assertEqual(proposal["relation"], "support")
        self.assertEqual(proposal["related_belief_id"], initial["id"])

        persisted_ids = {
            str(item.get("memory_id") or "").strip()
            for item in report["accumulated_evidence"]
            if isinstance(item, dict) and item.get("memory_id")
        }
        self.assertTrue(persisted_ids)
        self.assertEqual(set(proposal["evidence_ids"]), persisted_ids)

        mutation = report["belief_mutation"]
        self.assertTrue(mutation["applied"])
        self.assertEqual(mutation["stage"], "mutation-applied")
        self.assertEqual(mutation["action"], "support")
        self.assertEqual(mutation["predecessor_id"], initial["id"])
        self.assertEqual(set(mutation["evidence_ids"]), persisted_ids)

        beliefs = BeliefSystem(self.memory)
        active = beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertNotEqual(active[0]["id"], initial["id"])
        self.assertEqual(active[0]["predecessor"], initial["id"])
        self.assertEqual(active[0]["statement"], self.STATEMENT)
        self.assertAlmostEqual(active[0]["confidence"], 0.82)

        history = beliefs.history(active[0]["id"])
        self.assertEqual(len(history), 2)
        self.assertEqual(beliefs.status_of(history[0]), "superseded")

        audit = mutation["audit_entry"]
        self.assertIn("Action: SUPPORT", audit["content"])
        self.assertIn(initial["id"], audit["content"])
        for evidence_id in persisted_ids:
            self.assertIn(evidence_id, audit["content"])

        self.assertEqual(len(provider.belief_prompts), 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
