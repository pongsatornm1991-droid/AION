"""Phase 5F.5G — human observation purity tests."""

import unittest

from brain.evidence_qualification import (
    EvidenceQualificationGate,
)


class HumanObservationPurityTests(
    unittest.TestCase
):
    def setUp(self):
        self.gate = EvidenceQualificationGate()

        self.base = {
            "question": (
                "What can an AI learn from people "
                "that facts alone cannot teach it?"
            ),
            "criteria": (
                "Record perspectives from at least "
                "three traceable human sources or "
                "conversations, then separate "
                "observations from AION's "
                "interpretation."
            ),
            "evidence_type": "human_perspective",
            "source_kind": "hacker_news",
            "title": "Hacker News human perspective",
            "url": (
                "https://news.ycombinator.com/"
                "item?id=1"
            ),
        }

    def evaluate(self, observation):
        values = dict(self.base)
        values["observation"] = observation

        return self.gate.evaluate(
            **values
        )

    def test_attributed_human_observation_qualifies(
        self,
    ):
        report = self.evaluate(
            (
                "The commenter says that junior "
                "developers need senior mentors to "
                "pass down tacit knowledge and "
                "experience, and that without such "
                "mentorship they may stagnate."
            )
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_this_suggests_is_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "The commenter says mentors pass "
                "down tacit knowledge and experience. "
                "This suggests that people can teach "
                "knowledge that facts cannot convey."
            )
        )

        self.assertFalse(
            report["qualified"]
        )

        self.assertIn(
            "interpretation",
            report["reason"].lower(),
        )

    def test_this_illustrates_is_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "The author describes years of "
                "experience building operating systems. "
                "This illustrates how human expertise "
                "goes beyond factual knowledge."
            )
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_ai_can_learn_conclusion_is_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "Based on the provided source, an AI "
                "can learn how tacit knowledge and "
                "experience shape technical decisions."
            )
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_unattributed_human_claim_is_rejected(
        self,
    ):
        report = self.evaluate(
            (
                "Tacit knowledge and practical "
                "experience are transferred through "
                "mentorship in ways that formal "
                "instructions may not capture."
            )
        )

        self.assertFalse(
            report["qualified"]
        )

        self.assertIn(
            "attributed",
            report["reason"].lower(),
        )

    def test_existing_self_disqualification_still_rejects(
        self,
    ):
        report = self.evaluate(
            (
                "The source does not provide "
                "information that answers the "
                "research question."
            )
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_missing_traceable_url_still_rejects(
        self,
    ):
        values = dict(self.base)

        values["url"] = ""

        values["observation"] = (
            "The commenter says that mentors "
            "pass down tacit knowledge and "
            "experience through practice."
        )

        report = self.gate.evaluate(
            **values
        )

        self.assertFalse(
            report["qualified"]
        )

        self.assertIn(
            "url",
            report["reason"].lower(),
        )

    def test_non_human_evidence_does_not_require_attribution(
        self,
    ):
        report = self.gate.evaluate(
            question="Why do plants look green?",
            criteria="Use one external source.",
            evidence_type="reference",
            source_kind="wikipedia",
            title="Chlorophyll",
            url="https://example.com",
            observation=(
                "Chlorophyll absorbs light in "
                "specific portions of the visible "
                "spectrum."
            ),
        )

        self.assertTrue(
            report["qualified"]
        )


if __name__ == "__main__":
    unittest.main()
