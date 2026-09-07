"""Tests for AION Phase 5F.3 / 5F.5E search-query planning."""

import unittest

from brain.search_query_planner import (
    SearchQueryPlanner,
)


class SearchQueryPlannerTests(
    unittest.TestCase
):
    def setUp(self):
        self.planner = (
            SearchQueryPlanner()
        )

    def test_experiential_human_perspective_uses_semantic_queries(
        self,
    ):
        question = (
            "What can an AI learn from people that facts "
            "alone cannot teach it?"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "human_perspective"
            ),
        )

        self.assertGreaterEqual(
            len(queries),
            3,
        )

        self.assertLessEqual(
            len(queries),
            5,
        )

        normalized = [
            query.lower()
            for query in queries
        ]

        self.assertIn(
            "tacit knowledge experience",
            normalized,
        )

        self.assertIn(
            "human judgment experience",
            normalized,
        )

        self.assertIn(
            "knowledge difficult to articulate",
            normalized,
        )

        self.assertNotIn(
            "ai human learning",
            normalized,
        )

        self.assertNotIn(
            question.lower(),
            normalized,
        )

    def test_experiential_detection_is_not_exact_question_match(
        self,
    ):
        question = (
            "Which kinds of knowledge can people gain "
            "through experience that factual information "
            "alone cannot teach?"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "human_perspective"
            ),
        )

        normalized = [
            query.lower()
            for query in queries
        ]

        self.assertIn(
            "tacit knowledge experience",
            normalized,
        )

        self.assertIn(
            "intuition learned through experience",
            normalized,
        )

    def test_plain_ai_human_learning_keeps_broad_family(
        self,
    ):
        question = (
            "How does AI learning differ from human learning?"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "human_perspective"
            ),
        )

        normalized = [
            query.lower()
            for query in queries
        ]

        self.assertIn(
            "ai human learning",
            normalized,
        )

        self.assertIn(
            "human experience ai",
            normalized,
        )

    def test_query_planner_is_bounded(
        self,
    ):
        question = (
            "What can an AI learn from people that facts "
            "alone cannot teach it?"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "human_perspective"
            ),
            max_queries=3,
        )

        self.assertEqual(
            len(queries),
            3,
        )

    def test_general_question_gets_compact_query(
        self,
    ):
        question = (
            "What are the main architectural differences "
            "between transformer models and recurrent "
            "neural networks?"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "general_external"
            ),
        )

        self.assertTrue(
            queries
        )

        self.assertTrue(
            any(
                len(query.split()) <= 5
                for query in queries
            )
        )

    def test_empty_question_returns_no_queries(
        self,
    ):
        queries = self.planner.plan(
            question="",
            evidence_type=(
                "human_perspective"
            ),
        )

        self.assertEqual(
            queries,
            [],
        )

    def test_queries_are_unique(
        self,
    ):
        question = (
            "AI AI human human learning learning"
        )

        queries = self.planner.plan(
            question=question,
            evidence_type=(
                "human_perspective"
            ),
        )

        lowered = [
            item.lower()
            for item in queries
        ]

        self.assertEqual(
            len(lowered),
            len(set(lowered)),
        )


if __name__ == "__main__":
    unittest.main()
