from datetime import datetime


class CognitiveAuditor:
    """
    AION cognitive audit layer.

    Audits a proposed conclusion before it is accepted
    as a reliable decision.
    """

    def __init__(self):
        self.last_audit = None

    def audit(
        self,
        question: str,
        conclusion: str,
        facts=None,
        inferences=None,
        uncertainties=None,
    ):
        facts = self._clean_list(facts)
        inferences = self._clean_list(inferences)
        uncertainties = self._clean_list(uncertainties)

        flags = []
        recommendations = []

        if not question or not question.strip():
            flags.append("Missing decision question.")

        if not conclusion or not conclusion.strip():
            flags.append("Missing conclusion.")

        if not facts:
            flags.append("No supporting facts.")
            recommendations.append(
                "Obtain at least one verifiable fact."
            )

        if not inferences:
            recommendations.append(
                "Separate direct evidence from reasoning."
            )

        if not uncertainties:
            flags.append("No uncertainty declaration.")
            recommendations.append(
                "Explicitly identify what remains unverified."
            )

        evidence_score = self._score_evidence(facts)
        reasoning_score = self._score_reasoning(
            facts,
            inferences
        )
        uncertainty_score = self._score_uncertainty(
            uncertainties
        )

        contradiction_flags = self._detect_contradictions(
            facts,
            inferences,
            uncertainties
        )

        flags.extend(contradiction_flags)

        risk = self._risk_level(
            evidence_score,
            reasoning_score,
            uncertainty_score,
            contradiction_flags
        )

        confidence = round(
            (
                evidence_score
                + reasoning_score
                + uncertainty_score
            ) / 15,
            2
        )

        if contradiction_flags:
            confidence = min(confidence, 0.30)

        if risk == "HIGH":
            recommendations.append(
                "Do not accept the conclusion without further verification."
            )
        elif risk == "MEDIUM":
            recommendations.append(
                "Seek additional evidence before treating the conclusion as reliable."
            )
        else:
            recommendations.append(
                "Conclusion is sufficiently supported for provisional use."
            )

        result = {
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "question": question.strip(),
            "conclusion": conclusion.strip(),
            "scores": {
                "evidence": evidence_score,
                "reasoning": reasoning_score,
                "uncertainty": uncertainty_score,
            },
            "confidence": confidence,
            "risk": risk,
            "flags": flags,
            "recommendations": recommendations,
            "auditable": len(flags) == 0,
        }

        self.last_audit = result

        return result

    def _clean_list(self, values):
        if not values:
            return []

        return [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

    def _score_evidence(self, facts):
        count = len(facts)

        if count == 0:
            return 0

        if count == 1:
            return 2

        if count == 2:
            return 3

        return 5

    def _score_reasoning(self, facts, inferences):
        if not inferences:
            return 1 if facts else 0

        if not facts:
            return 0

        ratio = len(facts) / max(
            len(inferences),
            1
        )

        if ratio >= 3:
            return 5

        if ratio >= 2:
            return 4

        if ratio >= 1:
            return 3

        return 2

    def _score_uncertainty(self, uncertainties):
        count = len(uncertainties)

        if count == 0:
            return 0

        if count == 1:
            return 3

        if count == 2:
            return 4

        return 5

    def _detect_contradictions(
        self,
        facts,
        inferences,
        uncertainties,
    ):
        flags = []

        combined = (
            facts
            + inferences
            + uncertainties
        )

        positive_terms = (
            "verified",
            "confirmed",
            "certain",
            "proven",
            "reliable",
        )

        negative_terms = (
            "unverified",
            "unknown",
            "uncertain",
            "unsupported",
            "not verified",
        )

        has_positive = any(
            any(term in text.lower() for term in positive_terms)
            for text in combined
        )

        has_negative = any(
            any(term in text.lower() for term in negative_terms)
            for text in combined
        )

        if has_positive and has_negative:
            flags.append(
                "Potential conflict between certainty and uncertainty claims."
            )

        return flags

    def _risk_level(
        self,
        evidence,
        reasoning,
        uncertainty,
        contradictions,
    ):
        if contradictions:
            return "HIGH"

        if evidence <= 1:
            return "HIGH"

        if reasoning <= 1:
            return "HIGH"

        if uncertainty <= 1:
            return "HIGH"

        average = (
            evidence
            + reasoning
            + uncertainty
        ) / 3

        if average < 2.5:
            return "HIGH"

        if average < 4:
            return "MEDIUM"

        return "LOW"

    def summary(self):
        if not self.last_audit:
            return {
                "has_audit": False
            }

        return {
            "has_audit": True,
            "timestamp": self.last_audit["timestamp"],
            "confidence": self.last_audit["confidence"],
            "risk": self.last_audit["risk"],
            "flags": len(
                self.last_audit["flags"]
            ),
            "auditable": self.last_audit["auditable"],
        }