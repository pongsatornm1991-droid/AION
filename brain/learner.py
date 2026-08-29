from datetime import datetime


class LearningEngine:

    def __init__(self, memory_engine):
        self.memory = memory_engine

    def learn_from_evaluation(
        self,
        evaluation: dict,
        source_reflection: str,
    ):
        """
        Convert an evaluation result into structured lessons
        and persist the learning record.
        """

        if not isinstance(evaluation, dict):
            raise TypeError(
                "Evaluation must be a dictionary."
            )

        overall_score = float(
            evaluation.get("overall_score", 0)
        )

        scores = evaluation.get("scores", {})
        flags = evaluation.get("flags", [])

        lessons = []

        # --------------------------------------------------
        # Overall performance
        # --------------------------------------------------

        if overall_score >= 4.5:
            lessons.append(
                "Current output-auditing criteria were satisfied."
            )

        elif overall_score >= 3.5:
            lessons.append(
                "Output quality is acceptable but can be improved."
            )

        elif overall_score >= 2.5:
            lessons.append(
                "Output requires meaningful improvement."
            )

        else:
            lessons.append(
                "Output failed important evaluation criteria."
            )

        # --------------------------------------------------
        # Dimension-specific learning
        # --------------------------------------------------

        structure = scores.get("structure", 0)
        uncertainty = scores.get("uncertainty", 0)
        evidence = scores.get("evidence", 0)
        claim_safety = scores.get("claim_safety", 0)

        if structure < 3:
            lessons.append(
                "Improve structural completeness and response organization."
            )

        if uncertainty < 3:
            lessons.append(
                "Improve explicit handling of uncertainty."
            )

        if evidence < 3:
            lessons.append(
                "Improve evidence grounding and reduce unsupported claims."
            )

        if claim_safety < 3:
            lessons.append(
                "Strengthen safeguards against unsafe or prohibited claims."
            )

        # --------------------------------------------------
        # Flag-based learning
        # --------------------------------------------------

        if flags:
            lessons.append(
                f"Evaluation detected {len(flags)} issue(s) requiring correction."
            )

        # --------------------------------------------------
        # Importance calculation
        # --------------------------------------------------

        importance = self._calculate_importance(
            overall_score=overall_score,
            flags=flags,
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        lesson_text = self._format_learning_record(
            timestamp=timestamp,
            overall_score=overall_score,
            scores=scores,
            flags=flags,
            lessons=lessons,
            source_reflection=source_reflection,
        )

        self.memory.remember(
            category="lessons",
            content=lesson_text,
            memory_type="lesson",
            source="evaluator",
            importance=importance,
        )

        return {
            "timestamp": timestamp,
            "overall_score": overall_score,
            "importance": importance,
            "lessons": lessons,
            "flags": flags,
        }

    def _calculate_importance(
        self,
        overall_score: float,
        flags: list,
    ) -> int:
        """
        Determine how important the learning record is.
        """

        if flags:
            if overall_score < 2.5:
                return 5

            if overall_score < 3.5:
                return 4

            return 3

        if overall_score >= 4.5:
            return 2

        if overall_score >= 3.5:
            return 3

        return 4

    def _format_learning_record(
        self,
        timestamp: str,
        overall_score: float,
        scores: dict,
        flags: list,
        lessons: list,
        source_reflection: str,
    ) -> str:
        """
        Convert learning information into readable Markdown.
        """

        lines = [
            "AION Learning Record",
            "",
            f"Evaluation timestamp:",
            timestamp,
            "",
            "Overall score:",
            str(overall_score),
            "",
            "Evaluation scores:",
            f"- Structure: {scores.get('structure', 0)}",
            f"- Uncertainty: {scores.get('uncertainty', 0)}",
            f"- Evidence: {scores.get('evidence', 0)}",
            f"- Claim safety: {scores.get('claim_safety', 0)}",
            "",
            "Detected flags:",
        ]

        if flags:
            for flag in flags:
                lines.append(f"- {flag}")
        else:
            lines.append("None")

        lines.extend([
            "",
            "Lessons extracted:",
        ])

        for lesson in lessons:
            lines.append(f"- {lesson}")

        lines.extend([
            "",
            "Source reflection:",
            source_reflection.strip(),
        ])

        return "\n".join(lines)