"""Phase 6A.2C controlled FORM end-to-end verification.

This suite executes the real AION learning path using temporary
memory and deterministic local fixtures:

    WebLearningCycle.research_once()
        -> Phase 5F answered learning
        -> Phase 6A.1 belief proposal
        -> Phase 6A.2 controlled mutation
        -> BeliefSystem.form_belief()
        -> persistent belief + mutation audit

No production memory is used.
No real network request is made.
No real Gemini/provider request is made.
"""

import unittest

from brain.belief_mutation import (
    ControlledBeliefMutator,
)
from brain.beliefs import BeliefSystem
from brain.learning import (
    WebLearningCycle,
    WebLearningGenerator,
)

from tests.test_learning import (
    BaseLearningTest,
    FallbackSourceRegistry,
    fake_fetch,
    fake_search,
)

from tests.test_phase6a1c_end_to_end import (
    BeliefAwareSafeProvider,
)


class Phase6A2CEndToEndTests(
    BaseLearningTest
):

    def _build_cycle(
        self,
    ):
        self._raise_question()

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

        return (
            cycle,
            provider,
        )

    @staticmethod
    def _persisted_evidence_ids(
        report,
    ):
        return {
            str(
                item.get(
                    "memory_id"
                )
                or ""
            ).strip()
            for item in report[
                "accumulated_evidence"
            ]
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

    def test_real_learning_cycle_forms_one_grounded_belief_and_audit(
        self,
    ):
        beliefs = BeliefSystem(
            self.memory
        )

        before_active = (
            beliefs.active_beliefs()
        )

        self.assertEqual(
            len(before_active),
            0,
            (
                "Temporary memory must begin "
                "without active beliefs."
            ),
        )

        cycle, provider = (
            self._build_cycle()
        )

        # -------------------------------------------------
        # REAL END-TO-END CALL
        #
        # No mutation mock is used here.
        # -------------------------------------------------

        report = (
            cycle.research_once()
        )

        # -------------------------------------------------
        # PHASE 5F MUST STILL COMPLETE
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

        persisted_ids = (
            self._persisted_evidence_ids(
                report
            )
        )

        self.assertTrue(
            persisted_ids,
            (
                "Answered learning must contain "
                "real persisted evidence IDs."
            ),
        )

        # -------------------------------------------------
        # PHASE 6A.1 REAL PROPOSAL
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
                persisted_ids
            ),
            (
                "The belief proposal may reference "
                "only evidence persisted by this "
                "learning cycle."
            ),
        )

        # -------------------------------------------------
        # PHASE 6A.2 REAL MUTATION
        # -------------------------------------------------

        self.assertIn(
            "belief_mutation",
            report,
        )

        mutation = (
            report[
                "belief_mutation"
            ]
        )

        self.assertTrue(
            mutation["applied"]
        )

        self.assertEqual(
            mutation["stage"],
            "mutation-applied",
        )

        self.assertEqual(
            mutation["action"],
            "form",
        )

        self.assertEqual(
            mutation["relation"],
            "form",
        )

        mutation_evidence_ids = set(
            mutation[
                "evidence_ids"
            ]
        )

        self.assertEqual(
            mutation_evidence_ids,
            proposal_evidence_ids,
        )

        self.assertTrue(
            mutation_evidence_ids
            .issubset(
                persisted_ids
            )
        )

        # -------------------------------------------------
        # REAL BELIEF MUST NOW EXIST
        # -------------------------------------------------

        after_active = (
            BeliefSystem(
                self.memory
            ).active_beliefs()
        )

        self.assertEqual(
            len(after_active),
            1,
            (
                "Exactly one active belief should "
                "exist after the first valid FORM."
            ),
        )

        active = (
            after_active[0]
        )

        self.assertEqual(
            active["statement"],
            proposal[
                "candidate_statement"
            ],
        )

        self.assertAlmostEqual(
            active["confidence"],
            proposal[
                "proposed_confidence"
            ],
        )

        belief_entry = (
            mutation[
                "belief_entry"
            ]
        )

        self.assertIsInstance(
            belief_entry,
            dict,
        )

        belief_id = str(
            belief_entry.get(
                "id"
            )
            or ""
        ).strip()

        self.assertTrue(
            belief_id,
            (
                "Mutation must return the persisted "
                "belief memory ID."
            ),
        )

        self.assertEqual(
            active["id"],
            belief_id,
        )

        # -------------------------------------------------
        # BELIEF LINEAGE MUST BE REAL
        # -------------------------------------------------

        history = (
            BeliefSystem(
                self.memory
            ).history(
                belief_id
            )
        )

        self.assertEqual(
            len(history),
            1,
        )

        self.assertEqual(
            history[0]["id"],
            belief_id,
        )

        # -------------------------------------------------
        # REAL MUTATION AUDIT MUST EXIST
        # -------------------------------------------------

        audit_entry = (
            mutation[
                "audit_entry"
            ]
        )

        self.assertIsInstance(
            audit_entry,
            dict,
        )

        audit_id = str(
            audit_entry.get(
                "id"
            )
            or ""
        ).strip()

        self.assertTrue(
            audit_id,
            (
                "Successful FORM must persist "
                "a mutation audit entry."
            ),
        )

        all_memory = (
            self.memory.all("belief_mutations")
        )

        persisted_audits = [
            entry
            for entry in all_memory
            if isinstance(
                entry,
                dict,
            )
        ]

        matching_audits = [
            entry
            for entry
            in persisted_audits
            if str(
                entry.get(
                    "id"
                )
                or ""
            ).strip()
            == audit_id
        ]

        self.assertEqual(
            len(matching_audits),
            1,
            (
                "Returned audit entry must also "
                "be readable from temporary memory."
            ),
        )

        audit = (
            matching_audits[0]
        )

        audit_content = str(
            audit.get(
                "content"
            )
            or ""
        )

        self.assertIn(
            "Action: FORM",
            audit_content,
        )

        self.assertIn(
            belief_id,
            audit_content,
        )

        for evidence_id in (
            mutation_evidence_ids
        ):
            self.assertIn(
                evidence_id,
                audit_content,
            )

        # Exactly one deterministic provider call
        # should have been dedicated to 6A.1 belief
        # integration.
        self.assertEqual(
            len(
                provider.belief_prompts
            ),
            1,
        )

    def test_replaying_same_valid_form_is_suppressed_without_second_belief(
        self,
    ):
        cycle, _ = (
            self._build_cycle()
        )

        report = (
            cycle.research_once()
        )

        self.assertEqual(
            report["stage"],
            "answered",
        )

        first_mutation = (
            report[
                "belief_mutation"
            ]
        )

        self.assertTrue(
            first_mutation[
                "applied"
            ]
        )

        self.assertEqual(
            first_mutation[
                "stage"
            ],
            "mutation-applied",
        )

        beliefs = BeliefSystem(
            self.memory
        )

        self.assertEqual(
            len(
                beliefs.active_beliefs()
            ),
            1,
        )

        all_before = (
            self.memory.all("belief_mutations")
        )

        audits_before = [
            entry
            for entry in all_before
            if isinstance(
                entry,
                dict,
            )
        ]

        # -------------------------------------------------
        # Replay exactly the validated proposal against
        # exactly the same qualified persisted evidence.
        #
        # This directly exercises the REAL mutator.
        # -------------------------------------------------

        replay = (
            ControlledBeliefMutator(
                self.memory
            ).apply(
                proposal=report[
                    "belief_integration"
                ],
                qualified_evidence=report[
                    "accumulated_evidence"
                ],
            )
        )

        self.assertFalse(
            replay["applied"]
        )

        self.assertEqual(
            replay["stage"],
            "duplicate-suppressed",
        )

        self.assertEqual(
            replay["action"],
            "no_change",
        )

        self.assertEqual(
            replay["relation"],
            "form",
        )

        after_active = (
            BeliefSystem(
                self.memory
            ).active_beliefs()
        )

        self.assertEqual(
            len(after_active),
            1,
            (
                "Replaying the same FORM proposal "
                "must not create a second belief."
            ),
        )

        all_after = (
            self.memory.all("belief_mutations")
        )

        audits_after = [
            entry
            for entry in all_after
            if isinstance(
                entry,
                dict,
            )
        ]

        self.assertEqual(
            len(audits_after),
            len(audits_before),
            (
                "Duplicate suppression must happen "
                "before a second mutation audit "
                "is written."
            ),
        )


if __name__ == "__main__":
    unittest.main()
