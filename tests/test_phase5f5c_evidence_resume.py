from __future__ import annotations

import unittest

from brain.learning import (
    ResearchEvidenceStore,
    WebLearningCycle,
    WebLearningGenerator,
)

import tests.test_learning as learning_tests

SafeProvider = learning_tests.SafeProvider


QUESTION = (
    "What can an AI learn from people "
    "that facts alone cannot teach it?"
)

CRITERIA = (
    "Record perspectives from at least three "
    "traceable human sources or conversations, "
    "then separate observations from AION's "
    "interpretation."
)


class DailyQuotaProvider:
    """Simulate Gemini daily/project quota exhaustion."""

    def __init__(self):
        self.calls = []

    def generate(
        self,
        prompt,
    ):
        self.calls.append(
            prompt
        )

        raise RuntimeError(
            "429 RESOURCE_EXHAUSTED: "
            "Quota exceeded for "
            "generativelanguage.googleapis.com/"
            "generate_content_free_tier_requests; "
            "quotaId: "
            "GenerateRequestsPerDayPerProjectPerModel-FreeTier; "
            "quotaValue: 20"
        )


class ResumeOnlyGenerator(
    WebLearningGenerator
):
    """Generation is allowed only for persisted-evidence synthesis.

    A call to draft_answer() means recovery incorrectly attempted
    to draft a newly retrieved source.
    """

    def draft_answer(
        self,
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Phase 5F.5C recovery attempted "
            "a new source draft instead of "
            "reusing persisted evidence."
        )


class NeverResearch:
    """Fail immediately if recovery performs retrieval."""

    def __init__(self):
        self.search_calls = 0
        self.fetch_calls = 0

    def search(
        self,
        *args,
        **kwargs,
    ):
        self.search_calls += 1

        raise AssertionError(
            "Phase 5F.5C recovery attempted "
            "an unnecessary search."
        )

    def fetch(
        self,
        *args,
        **kwargs,
    ):
        self.fetch_calls += 1

        raise AssertionError(
            "Phase 5F.5C recovery attempted "
            "an unnecessary fetch."
        )


class Phase5F5CEvidenceResumeTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        # Reuse the already-proven isolated memory/curiosity
        # fixture from the main learning-cycle tests.
        self.fixture = (
            learning_tests.WebLearningCycleTests(
                methodName=(
                    "test_live_draft_failure_"
                    "is_captured_and_retriable"
                )
            )
        )

        self.fixture.setUp()

        self.memory = (
            self.fixture.memory
        )

        self.curiosity = (
            self.fixture.curiosity
        )

        self.question = (
            self.fixture._raise_question(
                statement=QUESTION,
                criteria=CRITERIA,
            )
        )

        self.store = (
            ResearchEvidenceStore(
                self.memory,
                self.curiosity,
            )
        )

        self.root_id = (
            self.store.root_question_id(
                self.question
            )
        )

        self._seed_three_evidence_items()

    def tearDown(
        self,
    ):
        try:
            tear_down = getattr(
                self.fixture,
                "tearDown",
                None,
            )

            if callable(
                tear_down
            ):
                tear_down()

        finally:
            self.fixture.doCleanups()

    def _seed_three_evidence_items(
        self,
    ):
        observations = [
            (
                "The participant describes how lived "
                "experience changes judgment in ways "
                "that factual descriptions alone do "
                "not capture."
            ),
            (
                "The participant explains that human "
                "values and context shape decisions "
                "even when the underlying facts are "
                "the same."
            ),
            (
                "The participant describes ambiguity, "
                "emotion, and social consequences as "
                "knowledge learned through interaction "
                "rather than factual recall."
            ),
        ]

        for index, observation in enumerate(
            observations,
            start=1,
        ):
            self.store.remember(
                root_question_id=(
                    self.root_id
                ),
                current_question_id=(
                    self.question["id"]
                ),
                source_kind=(
                    "hacker_news"
                ),
                title=(
                    "Synthetic traceable "
                    f"human perspective {index}"
                ),
                url=(
                    "https://example.invalid/"
                    f"phase5f5c-human-{index}"
                ),
                observation=(
                    observation
                ),
            )

        qualifying = (
            self.store.all_for(
                self.root_id
            )
        )

        self.assertEqual(
            len(
                qualifying
            ),
            3,
        )

    def _current_open_question(
        self,
    ):
        matches = [
            item
            for item
            in self.curiosity.open_questions()
            if str(
                item.get(
                    "statement",
                    ""
                )
            ).strip()
            == QUESTION
        ]

        self.assertEqual(
            len(
                matches
            ),
            1,
        )

        return matches[0]

    def test_persisted_evidence_survives_quota_failure_without_attempt(
        self,
    ):
        before = (
            self._current_open_question()
        )

        attempts_before = (
            before.get(
                "attempts",
                0,
            )
        )

        never = (
            NeverResearch()
        )

        provider = (
            DailyQuotaProvider()
        )

        generator = (
            ResumeOnlyGenerator(
                provider
            )
        )

        cycle = (
            WebLearningCycle(
                self.memory,
                self.curiosity,
                generator,
                search_fn=(
                    never.search
                ),
                fetch_fn=(
                    never.fetch
                ),
            )
        )

        report = (
            cycle.research_once(
                question_entry=before
            )
        )

        self.assertEqual(
            report["stage"],
            "provider-quota-exhausted",
        )

        self.assertEqual(
            never.search_calls,
            0,
        )

        self.assertEqual(
            never.fetch_calls,
            0,
        )

        qualifying_after = (
            self.store.all_for(
                self.root_id
            )
        )

        self.assertEqual(
            len(
                qualifying_after
            ),
            3,
        )

        after = (
            self._current_open_question()
        )

        self.assertEqual(
            after.get(
                "attempts",
                0,
            ),
            attempts_before,
        )

        self.assertEqual(
            len(
                provider.calls
            ),
            1,
        )

    def test_next_cycle_reuses_persisted_evidence_and_answers(
        self,
    ):
        # ----------------------------------------------------
        # First recovery run: provider unavailable.
        # ----------------------------------------------------

        before = (
            self._current_open_question()
        )

        attempts_before = (
            before.get(
                "attempts",
                0,
            )
        )

        never1 = (
            NeverResearch()
        )

        failing_generator = (
            ResumeOnlyGenerator(
                DailyQuotaProvider()
            )
        )

        cycle1 = (
            WebLearningCycle(
                self.memory,
                self.curiosity,
                failing_generator,
                search_fn=(
                    never1.search
                ),
                fetch_fn=(
                    never1.fetch
                ),
            )
        )

        report1 = (
            cycle1.research_once(
                question_entry=before
            )
        )

        self.assertEqual(
            report1["stage"],
            "provider-quota-exhausted",
        )

        self.assertEqual(
            len(
                self.store.all_for(
                    self.root_id
                )
            ),
            3,
        )

        # ----------------------------------------------------
        # Second run: provider recovered.
        #
        # Search, fetch, and draft are still forbidden.
        # The cycle must synthesize from the same persisted
        # three qualifying evidence records.
        # ----------------------------------------------------

        still_open = (
            self._current_open_question()
        )

        self.assertEqual(
            still_open.get(
                "attempts",
                0,
            ),
            attempts_before,
        )

        never2 = (
            NeverResearch()
        )

        safe_provider = (
            SafeProvider(
                text=(
                    "Observations from three traceable "
                    "human perspectives show that people "
                    "can teach an AI about lived context, "
                    "judgment, values, ambiguity, and "
                    "social consequences that factual "
                    "statements alone do not fully convey. "
                    "AION interprets these observations "
                    "as evidence that interaction can add "
                    "contextual and value-sensitive forms "
                    "of learning beyond factual recall."
                ),
                criteria_satisfied=True,
            )
        )

        recovered_generator = (
            ResumeOnlyGenerator(
                safe_provider
            )
        )

        cycle2 = (
            WebLearningCycle(
                self.memory,
                self.curiosity,
                recovered_generator,
                search_fn=(
                    never2.search
                ),
                fetch_fn=(
                    never2.fetch
                ),
            )
        )

        report2 = (
            cycle2.research_once(
                question_entry=still_open
            )
        )

        self.assertEqual(
            never2.search_calls,
            0,
        )

        self.assertEqual(
            never2.fetch_calls,
            0,
        )

        self.assertEqual(
            report2["stage"],
            "answered",
        )

        self.assertTrue(
            report2["researched"]
        )

        self.assertEqual(
            len(
                report2[
                    "accumulated_evidence"
                ]
            ),
            3,
        )

        # The question must now be resolved.
        remaining = [
            item
            for item
            in self.curiosity.open_questions()
            if str(
                item.get(
                    "statement",
                    ""
                )
            ).strip()
            == QUESTION
        ]

        self.assertEqual(
            remaining,
            [],
        )


if __name__ == "__main__":
    unittest.main()
