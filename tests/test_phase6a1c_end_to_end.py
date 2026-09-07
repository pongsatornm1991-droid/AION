"""Phase 6A.1C end-to-end verification.

This test executes the real WebLearningCycle.research_once() path
using the repository's already-proven temporary-memory learning
fixtures.

No network request is made.
No real provider is called.
Production memory is not used.
Belief mutation must remain disabled.
"""

import json
import unittest

from brain.beliefs import BeliefSystem
from brain.learning import (
    WebLearningCycle,
    WebLearningGenerator,
)

from tests.test_learning import (
    BaseLearningTest,
    FallbackSourceRegistry,
    SafeProvider,
    fake_fetch,
    fake_search,
)


class BeliefAwareSafeProvider(
    SafeProvider
):
    """Existing deterministic learning provider + 6A proposal response."""

    BELIEF_PROMPT_MARKER = (
        "You are AION's evidence-to-belief "
        "proposal evaluator."
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.belief_prompts = []

    @staticmethod
    def _proposal_from_prompt(
        prompt,
    ):
        evidence_marker = (
            "QUALIFIED EVIDENCE:\n"
        )

        beliefs_marker = (
            "\n\nACTIVE BELIEFS:"
        )

        if evidence_marker not in prompt:
            raise AssertionError(
                "Belief integration prompt is missing "
                "the qualified-evidence section."
            )

        evidence_text = (
            prompt
            .split(
                evidence_marker,
                1,
            )[1]
            .split(
                beliefs_marker,
                1,
            )[0]
            .strip()
        )

        evidence = json.loads(
            evidence_text
        )

        if not isinstance(
            evidence,
            list,
        ):
            raise AssertionError(
                "Qualified evidence payload must "
                "be a list."
            )

        evidence_ids = [
            str(item.get("id") or "").strip()
            for item in evidence
            if isinstance(item, dict)
            and str(
                item.get("id") or ""
            ).strip()
        ]

        if not evidence_ids:
            raise AssertionError(
                "End-to-end belief proposal received "
                "no real evidence IDs."
            )

        return json.dumps({
            "relation": "form",
            "candidate_statement": (
                "External evidence can support a "
                "provisional evidence-grounded belief."
            ),
            "related_belief_id": None,
            "proposed_confidence": 0.72,
            "reason": (
                "The completed learning cycle supplied "
                "traceable qualified evidence."
            ),
            "evidence_ids": evidence_ids,
        })

    def generate(
        self,
        prompt,
    ):
        if (
            self.BELIEF_PROMPT_MARKER
            in prompt
        ):
            self.belief_prompts.append(
                prompt
            )

            return (
                self._proposal_from_prompt(
                    prompt
                )
            )

        return super().generate(
            prompt
        )


class Phase6A1CEndToEndTests(
    BaseLearningTest
):

    def test_real_learning_cycle_returns_grounded_belief_proposal_without_mutation(
        self,
    ):
        # Use the same successful fallback-learning fixture
        # already proven by tests/test_learning.py.

        self._raise_question()

        beliefs = BeliefSystem(
            self.memory
        )

        before_active = (
            beliefs.active_beliefs()
        )

        self.assertEqual(
            len(before_active),
            0,
            "Temporary test memory should begin "
            "without active beliefs.",
        )

        provider = (
            BeliefAwareSafeProvider(
                criteria_satisfied=True
            )
        )

        generator = (
            WebLearningGenerator(
                provider
            )
        )

        cycle = WebLearningCycle(
            self.memory,
            self.curiosity,
            generator,
            search_fn=fake_search(
                []
            ),
            fetch_fn=fake_fetch(
                {}
            ),
            source_registry=(
                FallbackSourceRegistry()
            ),
            fallback_search_fn=(
                fake_search([
                    "2301.12345"
                ])
            ),
            fallback_fetch_fn=(
                fake_fetch({
                    "2301.12345": {
                        "title": (
                            "A Paper About Plants"
                        ),
                        "url": (
                            "https://arxiv.org/"
                            "abs/2301.12345"
                        ),
                        "extract": (
                            "This paper studies "
                            "plant pigments."
                        ),
                    }
                })
            ),
        )

        report = (
            cycle.research_once()
        )

        # -------------------------------------------------
        # Phase 5F must still complete normally.
        # -------------------------------------------------

        self.assertTrue(
            report["researched"]
        )

        self.assertEqual(
            report["stage"],
            "answered",
        )

        self.assertIn(
            "semantic_entry",
            report,
        )

        self.assertIn(
            "resolved_question",
            report,
        )

        self.assertIn(
            "accumulated_evidence",
            report,
        )

        accumulated = (
            report[
                "accumulated_evidence"
            ]
        )

        self.assertTrue(
            accumulated,
            "Answered learning must contain "
            "accumulated evidence.",
        )

        real_evidence_ids = {
            str(
                item.get(
                    "memory_id"
                )
                or ""
            ).strip()
            for item in accumulated
            if isinstance(
                item,
                dict,
            )
            and str(
                item.get(
                    "memory_id"
                )
                or ""
            ).strip()
        }

        self.assertTrue(
            real_evidence_ids,
            "Accumulated evidence must contain "
            "persisted memory IDs.",
        )

        # -------------------------------------------------
        # Phase 6A.1B must execute through the real
        # learning return path.
        # -------------------------------------------------

        self.assertIn(
            "belief_integration",
            report,
        )

        proposal = (
            report[
                "belief_integration"
            ]
        )

        self.assertEqual(
            proposal["stage"],
            "proposed",
        )

        self.assertEqual(
            proposal["action"],
            "form",
        )

        self.assertEqual(
            proposal["relation"],
            "form",
        )

        self.assertIsNone(
            proposal[
                "related_belief_id"
            ]
        )

        self.assertGreater(
            proposal[
                "proposed_confidence"
            ],
            0.0,
        )

        self.assertLessEqual(
            proposal[
                "proposed_confidence"
            ],
            1.0,
        )

        proposal_evidence_ids = set(
            proposal[
                "evidence_ids"
            ]
        )

        self.assertTrue(
            proposal_evidence_ids
        )

        self.assertTrue(
            proposal_evidence_ids
            .issubset(
                real_evidence_ids
            ),
            (
                "Belief proposal must reference "
                "only evidence IDs actually persisted "
                "by this learning cycle."
            ),
        )

        # Exactly one dedicated 6A proposal call should occur.
        self.assertEqual(
            len(
                provider.belief_prompts
            ),
            1,
        )

        # -------------------------------------------------
        # Most important Phase 6A.1 safety assertion:
        # proposal generation must NOT mutate beliefs.
        # -------------------------------------------------

        after_active = (
            BeliefSystem(
                self.memory
            ).active_beliefs()
        )

        self.assertEqual(
            len(after_active),
            0,
            (
                "Phase 6A.1 must not form, revise, "
                "or retract beliefs."
            ),
        )

        self.assertEqual(
            before_active,
            after_active,
        )


if __name__ == "__main__":
    unittest.main()
