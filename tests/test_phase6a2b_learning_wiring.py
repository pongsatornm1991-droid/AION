"""Phase 6A.2B learning wiring tests.

These tests verify that the real answered learning path now passes
the Phase 6A.1 proposal into the bounded Phase 6A.2 mutation layer.

The mutation function is mocked here. Phase 6A.2C will test the
real persistent mutation end-to-end.
"""

import unittest
from unittest.mock import patch

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


class Phase6A2BLearningWiringTests(
    BaseLearningTest
):

    def _cycle(
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

    def test_answered_learning_calls_mutation_layer(
        self,
    ):
        cycle, _ = self._cycle()

        captured = {}

        def fake_mutation(
            *,
            memory,
            proposal,
            qualified_evidence,
        ):
            captured["memory"] = memory
            captured["proposal"] = proposal
            captured["evidence"] = (
                qualified_evidence
            )

            return {
                "stage": "mutation-applied",
                "applied": True,
                "action": "form",
                "relation": "form",
                "belief_entry": {
                    "id": "test-belief"
                },
                "audit_entry": {
                    "id": "test-audit"
                },
                "reason": "test",
                "evidence_ids": (
                    proposal[
                        "evidence_ids"
                    ]
                ),
            }

        with patch(
            "brain.belief_mutation."
            "safely_apply_belief_mutation",
            side_effect=fake_mutation,
        ):
            report = (
                cycle.research_once()
            )

        self.assertEqual(
            report["stage"],
            "answered",
        )

        self.assertEqual(
            report[
                "belief_mutation"
            ][
                "stage"
            ],
            "mutation-applied",
        )

        self.assertIs(
            captured["memory"],
            self.memory,
        )

        self.assertEqual(
            captured["proposal"],
            report[
                "belief_integration"
            ],
        )

        self.assertEqual(
            captured["evidence"],
            report[
                "accumulated_evidence"
            ],
        )

    def test_mutation_receives_real_persisted_evidence_ids(
        self,
    ):
        cycle, _ = self._cycle()

        captured = {}

        def fake_mutation(
            *,
            memory,
            proposal,
            qualified_evidence,
        ):
            captured["proposal"] = (
                proposal
            )

            captured["evidence"] = (
                qualified_evidence
            )

            return {
                "stage": "mutation-blocked",
                "applied": False,
                "action": "no_change",
                "relation": "form",
                "belief_entry": None,
                "audit_entry": None,
                "reason": "test",
            }

        with patch(
            "brain.belief_mutation."
            "safely_apply_belief_mutation",
            side_effect=fake_mutation,
        ):
            report = (
                cycle.research_once()
            )

        persisted_ids = {
            str(
                item.get(
                    "memory_id"
                )
                or ""
            ).strip()
            for item in captured[
                "evidence"
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

        proposal_ids = set(
            captured[
                "proposal"
            ][
                "evidence_ids"
            ]
        )

        self.assertTrue(
            persisted_ids
        )

        self.assertTrue(
            proposal_ids
        )

        self.assertTrue(
            proposal_ids.issubset(
                persisted_ids
            )
        )

        self.assertEqual(
            report["stage"],
            "answered",
        )

    def test_mutation_exception_does_not_break_answered_learning(
        self,
    ):
        cycle, _ = self._cycle()

        with patch(
            "brain.belief_mutation."
            "safely_apply_belief_mutation",
            side_effect=RuntimeError(
                "simulated mutation failure"
            ),
        ):
            report = (
                cycle.research_once()
            )

        self.assertEqual(
            report["stage"],
            "answered",
        )

        self.assertEqual(
            report[
                "belief_mutation"
            ][
                "stage"
            ],
            "mutation-error",
        )

        self.assertFalse(
            report[
                "belief_mutation"
            ][
                "applied"
            ]
        )

        self.assertEqual(
            report[
                "belief_mutation"
            ][
                "action"
            ],
            "no_change",
        )

        self.assertIn(
            "simulated mutation failure",
            report[
                "belief_mutation"
            ][
                "error"
            ],
        )

    def test_mutation_runs_after_belief_proposal_exists(
        self,
    ):
        cycle, _ = self._cycle()

        seen = {}

        def fake_mutation(
            *,
            memory,
            proposal,
            qualified_evidence,
        ):
            seen["stage"] = (
                proposal.get(
                    "stage"
                )
            )

            seen["action"] = (
                proposal.get(
                    "action"
                )
            )

            return {
                "stage": "mutation-blocked",
                "applied": False,
                "action": "no_change",
                "relation": (
                    proposal.get(
                        "relation"
                    )
                ),
                "belief_entry": None,
                "audit_entry": None,
                "reason": "test",
            }

        with patch(
            "brain.belief_mutation."
            "safely_apply_belief_mutation",
            side_effect=fake_mutation,
        ):
            report = (
                cycle.research_once()
            )

        self.assertEqual(
            seen["stage"],
            "proposed",
        )

        self.assertEqual(
            seen["action"],
            "form",
        )

        self.assertEqual(
            report[
                "belief_integration"
            ][
                "stage"
            ],
            "proposed",
        )

    def test_return_contains_both_integration_and_mutation_reports(
        self,
    ):
        cycle, _ = self._cycle()

        with patch(
            "brain.belief_mutation."
            "safely_apply_belief_mutation",
            return_value={
                "stage": "mutation-blocked",
                "applied": False,
                "action": "no_change",
                "relation": "form",
                "belief_entry": None,
                "audit_entry": None,
                "reason": "test",
            },
        ):
            report = (
                cycle.research_once()
            )

        self.assertIn(
            "belief_integration",
            report,
        )

        self.assertIn(
            "belief_mutation",
            report,
        )

        self.assertEqual(
            report["stage"],
            "answered",
        )

    def test_source_contains_ordered_phase6a2b_wiring(
        self,
    ):
        from pathlib import Path
        import brain.learning

        path = Path(
            brain.learning.__file__
        )

        source = path.read_text(
            encoding="utf-8"
        )

        integration_index = (
            source.index(
                "PHASE 6A.1B"
            )
        )

        mutation_index = (
            source.index(
                "PHASE 6A.2B"
            )
        )

        return_index = (
            source.index(
                '"belief_mutation"'
            )
        )

        self.assertLess(
            integration_index,
            mutation_index,
        )

        self.assertLess(
            mutation_index,
            return_index,
        )

        self.assertIn(
            "safely_apply_belief_mutation",
            source,
        )


if __name__ == "__main__":
    unittest.main()
