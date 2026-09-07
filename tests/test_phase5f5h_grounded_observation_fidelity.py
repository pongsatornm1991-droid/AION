"""Tests for Phase 5F.5H grounded observation fidelity."""

import unittest

from brain.evidence_qualification import (
    EvidenceQualificationGate,
)


class GroundedObservationFidelityTests(
    unittest.TestCase
):
    def setUp(self):
        self.gate = EvidenceQualificationGate()

        self.common = {
            "question": (
                "What can an AI learn from people "
                "that facts alone cannot teach it?"
            ),
            "criteria": (
                "Record perspectives from at least "
                "three traceable human sources."
            ),
            "evidence_type": "human_perspective",
            "source_kind": "hacker_news",
            "title": "Human comment",
            "url": (
                "https://news.ycombinator.com/"
                "item?id=1"
            ),
        }

    def evaluate(
        self,
        source_extract,
        observation,
    ):
        values = dict(self.common)

        values["source_extract"] = (
            source_extract
        )

        values["observation"] = (
            observation
        )

        return self.gate.evaluate(
            **values
        )

    def test_plain_grounded_observation_passes(
        self,
    ):
        report = self.evaluate(
            (
                "Engineering work relies on "
                "tacit knowledge, experience, "
                "and team cohesion."
            ),
            (
                "The commenter says engineering "
                "work relies on tacit knowledge, "
                "experience, and team cohesion."
            ),
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_unsupported_intentionally_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "Workers may quit or write "
                "obscure code."
            ),
            (
                "The commenter says workers may "
                "quit or intentionally write "
                "obscure code."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

        self.assertIn(
            "fidelity",
            report["reason"].lower(),
        )

    def test_supported_intentionally_allowed(
        self,
    ):
        report = self.evaluate(
            (
                "Workers intentionally wrote "
                "obscure code."
            ),
            (
                "The commenter says workers "
                "intentionally wrote obscure code."
            ),
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_unsupported_incredible_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "They produced more than "
                "100K lines in one year."
            ),
            (
                "The commenter says they produced "
                "an incredible amount of code "
                "in one year."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_unsupported_strictly_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "Without mentorship they may "
                "have to prompt to deliver."
            ),
            (
                "The commenter says without "
                "mentorship they may rely strictly "
                "on prompts to deliver."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_missing_raw_source_is_legacy_safe(
        self,
    ):
        values = dict(self.common)

        values["observation"] = (
            "The commenter says practical "
            "experience matters."
        )

        report = self.gate.evaluate(
            **values
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_nonhuman_evidence_unchanged(
        self,
    ):
        report = self.gate.evaluate(
            question="Test question",
            criteria="Use a source.",
            evidence_type="reference",
            source_kind="reference",
            title="Reference",
            url="https://example.com",
            source_extract=(
                "The result was measured."
            ),
            observation=(
                "The result was clearly measured."
            ),
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_5f5g_interpretation_gate_remains(
        self,
    ):
        report = self.evaluate(
            (
                "Mentors pass down tacit "
                "knowledge and experience."
            ),
            (
                "The commenter says mentors pass "
                "down tacit knowledge. "
                "This suggests AI can learn "
                "from mentors."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )


if __name__ == "__main__":
    unittest.main()
