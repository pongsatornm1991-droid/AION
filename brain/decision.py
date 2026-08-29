from datetime import datetime


class DecisionEngine:
    """
    AION Decision Engine

    Evaluates a decision using:
    - available facts
    - reasoned inferences
    - uncertainties
    - candidate options
    - confidence
    """

    def __init__(self):
        self.last_decision = None

    def evaluate(
        self,
        question: str,
        options=None,
        facts=None,
        inferences=None,
        uncertainties=None,
    ):
        """
        Evaluate a decision context.

        Returns a structured decision record.
        """

        question = str(question).strip()

        if not question:
            raise ValueError("Decision question cannot be empty.")

        options = options or []
        facts = facts or []
        inferences = inferences or []
        uncertainties = uncertainties or []

        if not isinstance(options, list):
            raise TypeError("Options must be a list.")

        if not isinstance(facts, list):
            raise TypeError("Facts must be a list.")

        if not isinstance(inferences, list):
            raise TypeError("Inferences must be a list.")

        if not isinstance(uncertainties, list):
            raise TypeError("Uncertainties must be a list.")

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        evidence_score = self._score_evidence(
            facts=facts,
            uncertainties=uncertainties,
        )

        reasoning_score = self._score_reasoning(
            inferences=inferences,
            facts=facts,
        )

        uncertainty_score = self._score_uncertainty(
            uncertainties
        )

        confidence = self._calculate_confidence(
            evidence_score=evidence_score,
            reasoning_score=reasoning_score,
            uncertainty_score=uncertainty_score,
        )

        result = {
            "timestamp": timestamp,
            "question": question,
            "options": options,
            "facts": facts,
            "inferences": inferences,
            "uncertainties": uncertainties,
            "scores": {
                "evidence": evidence_score,
                "reasoning": reasoning_score,
                "uncertainty": uncertainty_score,
            },
            "confidence": confidence,
        }

        self.last_decision = result

        return result

    def _score_evidence(self, facts, uncertainties):
        """
        Score evidence quality from 0 to 5.

        This scale is shared with CognitiveAuditor so a decision
        confidence and its audit confidence describe the same
        evidence standard.
        """

        fact_count = len(facts)
        uncertainty_count = len(uncertainties)

        if fact_count == 0:
            return 0

        if fact_count == 1:
            return 2

        if fact_count == 2:
            return 3

        return 5

    def _score_reasoning(self, inferences, facts):
        """
        Score reasoning quality from 0 to 5.

        Reasoning strength depends on the balance between direct facts
        and inferences, rather than the raw number of inferences.
        """

        if not inferences:
            return 0

        if not facts:
            return 0

        ratio = len(facts) / len(inferences)

        if ratio >= 3:
            return 5

        if ratio >= 2:
            return 4

        if ratio >= 1:
            return 3

        return 2

    def _score_uncertainty(self, uncertainties):
        """
        Score uncertainty handling from 0 to 5.

        Explicit uncertainty is considered a positive
        property of a decision system.
        """

        if not uncertainties:
            return 0

        if len(uncertainties) == 1:
            return 3

        if len(uncertainties) == 2:
            return 4

        return 5

    def _calculate_confidence(
        self,
        evidence_score,
        reasoning_score,
        uncertainty_score,
    ):
        """
        Calculate overall confidence from 0 to 1.
        """

        total = (
            evidence_score
            + reasoning_score
            + uncertainty_score
        )

        confidence = total / 15

        return round(
            max(0.0, min(1.0, confidence)),
            2,
        )

    def summary(self):
        """
        Return a compact representation of the latest decision.
        """

        if self.last_decision is None:
            return {
                "has_decision": False,
                "confidence": 0.0,
            }

        return {
            "has_decision": True,
            "timestamp": self.last_decision["timestamp"],
            "question": self.last_decision["question"],
            "confidence": self.last_decision["confidence"],
            "scores": self.last_decision["scores"],
        }
