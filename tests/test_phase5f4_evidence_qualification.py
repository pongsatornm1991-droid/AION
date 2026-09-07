import unittest

from brain.evidence_qualification import (
    EvidenceQualificationGate,
)


class EvidenceQualificationGateTests(
    unittest.TestCase
):
    def setUp(self):
        self.gate = EvidenceQualificationGate()

    def test_rejects_real_daveguy_observation(
        self,
    ):
        report = self.gate.evaluate(
            question=(
                "What can an AI learn from people "
                "that facts alone cannot teach it?"
            ),
            criteria=(
                "Record perspectives from at least "
                "three traceable human sources or conversations."
            ),
            evidence_type="human_perspective",
            source_kind="hacker_news",
            title=(
                "Hacker News perspective by daveguy "
                "(comment 47534046)"
            ),
            url=(
                "https://news.ycombinator.com/"
                "item?id=47534046"
            ),
            observation=(
                "Based on the provided source, there is no "
                "information explaining what an AI can learn "
                "from people that facts alone cannot teach it. "
                "The source instead focuses on the structural "
                "gap in how learning occurs."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_rejects_real_vonneumannstan_observation(
        self,
    ):
        report = self.gate.evaluate(
            question=(
                "What can an AI learn from people "
                "that facts alone cannot teach it?"
            ),
            evidence_type="human_perspective",
            source_kind="hacker_news",
            title=(
                "Hacker News perspective by "
                "vonneumannstan (comment 47530769)"
            ),
            url=(
                "https://news.ycombinator.com/"
                "item?id=47530769"
            ),
            observation=(
                "Based on the provided source, there is no "
                "information explaining what an AI can learn "
                "from people that facts alone cannot teach it. "
                "The source only discusses human versus AI "
                "learning efficiency and definitions of AGI."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_accepts_relevant_traceable_human_perspective(
        self,
    ):
        report = self.gate.evaluate(
            question=(
                "What can an AI learn from people "
                "that facts alone cannot teach it?"
            ),
            evidence_type="human_perspective",
            source_kind="hacker_news",
            title="Hacker News perspective by example",
            url=(
                "https://news.ycombinator.com/"
                "item?id=123"
            ),
            observation=(
                "The commenter argues that people can transmit "
                "tacit judgment, contextual expectations, and "
                "experience-dependent priorities that are hard "
                "to reduce to isolated factual statements."
            ),
        )

        self.assertTrue(
            report["qualified"]
        )

    def test_human_perspective_requires_url(
        self,
    ):
        report = self.gate.evaluate(
            question="How do people make judgments?",
            evidence_type="human_perspective",
            source_kind="hacker_news",
            title="A human perspective",
            url="",
            observation=(
                "The commenter describes how prior lived "
                "experience affects judgment under ambiguity."
            ),
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_rejects_empty_observation(
        self,
    ):
        report = self.gate.evaluate(
            question="A real question",
            evidence_type="general_external",
            observation="",
        )

        self.assertFalse(
            report["qualified"]
        )

    def test_self_disqualification_helper(
        self,
    ):
        self.assertTrue(
            self.gate.observation_self_disqualifies(
                "The source does not answer the research "
                "question and provides no useful information."
            )
        )

        self.assertFalse(
            self.gate.observation_self_disqualifies(
                "The source describes how tacit social judgment "
                "is learned through repeated interaction and "
                "contextual feedback."
            )
        )


if __name__ == "__main__":
    unittest.main()
