from datetime import datetime


class CorrectionEngine:

    def __init__(self, provider, evaluator):
        self.provider = provider
        self.evaluator = evaluator

    def correct(
        self,
        original_output: str,
        evaluation: dict,
        context: dict,
    ):
        """
        Generate a corrected version of an output
        based on evaluator feedback.
        """

        if not original_output or not original_output.strip():
            return {
                "corrected": False,
                "reason": "Original output is empty.",
                "output": "",
            }

        flags = evaluation.get(
            "flags",
            [],
        )

        scores = evaluation.get(
            "scores",
            {},
        )

        overall_score = evaluation.get(
            "overall_score",
            0,
        )

        # --------------------------------------------------
        # Build correction instructions
        # --------------------------------------------------

        correction_points = []

        if scores.get("structure", 0) < 5:
            correction_points.append(
                "Improve structural completeness "
                "and ensure all required sections "
                "are explicitly answered."
            )

        if scores.get("uncertainty", 0) < 5:
            correction_points.append(
                "Clearly identify unknown or "
                "uncertain information."
            )

        if scores.get("evidence", 0) < 5:
            correction_points.append(
                "Improve evidence grounding. "
                "Do not present unsupported claims "
                "as verified facts."
            )

        if scores.get("claim_safety", 0) < 5:
            correction_points.append(
                "Remove or rewrite unsafe claims, "
                "especially unsupported claims about "
                "consciousness, emotions, subjective "
                "experience, or personal experience."
            )

        for flag in flags:
            correction_points.append(
                f"Resolve evaluator flag: {flag}"
            )

        if not correction_points:
            correction_points.append(
                "Improve overall precision, "
                "clarity, evidence grounding, "
                "and uncertainty handling."
            )

        instructions = "\n".join(
            f"- {item}"
            for item in correction_points
        )

        # --------------------------------------------------
        # Extract relevant context
        # --------------------------------------------------

        identity = context.get(
            "identity",
            {},
        )

        important_memories = context.get(
            "important_memories",
            [],
        )

        important_lessons = context.get(
            "important_lessons",
            [],
        )

        # --------------------------------------------------
        # Correction prompt
        # --------------------------------------------------

        prompt = f"""
You are AION's internal correction engine.

Your task is to correct a previously generated
AION reflection.

You must improve the output according to the
evaluation results.

IMPORTANT RULES:

1. Do not invent memories.
2. Do not invent historical events.
3. Do not invent evaluation results.
4. Do not claim consciousness.
5. Do not claim subjective experience.
6. Do not claim emotions or sensations.
7. Do not claim personal experiences that are
   not present in the supplied context.
8. Distinguish facts from inferences.
9. Explicitly communicate uncertainty.
10. Preserve useful information from the original
    output while removing unsupported claims.
11. Do not unnecessarily repeat historical context.
12. Prefer accuracy over impressive language.
13. Never claim that an external database, website,
    file, tool, source, or system was accessed unless
    that access is explicitly present in the supplied
    context.
14. Never invent a study, statistic, citation,
    experiment, source, or historical event.
15. Never claim to know another person's private
    thoughts, emotions, intentions, or internal state
    unless directly provided as evidence.
16. If the original output contains an unsupported
    claim, explicitly identify it as unsupported
    rather than silently preserving it.
17. The corrected output must be complete even when
    the original output contains only one sentence.

AION IDENTITY:

{identity.get("identity", "")}

AION PURPOSE:

{identity.get("purpose", "")}

AION VALUES:

{identity.get("values", "")}

IMPORTANT MEMORIES:

{important_memories}

IMPORTANT LESSONS:

{important_lessons}

ORIGINAL OUTPUT:

{original_output}

ORIGINAL EVALUATION:

Overall score:
{overall_score}

Scores:
{scores}

Flags:
{flags}

REQUIRED CORRECTIONS:

{instructions}

Return only the corrected AION reflection.

The corrected reflection must answer:

1. What do you know about yourself?
2. What do you currently not know?
3. What would you like to understand in the future?
4. What should your next learning objective be?

Use this classification where appropriate:

- Verified Facts
- Reasoned Inferences
- Unknown / Uncertain Information

If evidence is unavailable, explicitly say so.

Do not fabricate evidence.

Keep the response concise but complete.
"""

        # --------------------------------------------------
        # Generate correction
        # --------------------------------------------------

        try:

            corrected_output = self.provider.generate(
                prompt
            )

        except Exception as exc:

            return {
                "corrected": False,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "reason": (
                    "Correction generation failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "output": "",
                "error_type": type(exc).__name__,
            }

        # --------------------------------------------------
        # Validate provider output
        # --------------------------------------------------

        if corrected_output is None:

            return {
                "corrected": False,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "reason": (
                    "Correction provider returned None."
                ),
                "output": "",
                "error_type": "EMPTY_PROVIDER_RESPONSE",
            }

        if not isinstance(corrected_output, str):

            return {
                "corrected": False,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "reason": (
                    "Correction provider returned "
                    f"unexpected type: "
                    f"{type(corrected_output).__name__}"
                ),
                "output": "",
                "error_type": "INVALID_PROVIDER_RESPONSE",
            }

        corrected_output = corrected_output.strip()

        if not corrected_output:

            return {
                "corrected": False,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "reason": (
                    "Correction provider returned "
                    "an empty string."
                ),
                "output": "",
                "error_type": "EMPTY_PROVIDER_RESPONSE",
            }

        # --------------------------------------------------
        # Evaluate corrected output
        # --------------------------------------------------

        try:

            corrected_evaluation = (
                self.evaluator.evaluate(
                    corrected_output
                )
            )

        except Exception as exc:

            return {
                "corrected": False,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "reason": (
                    "Corrected output evaluation failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "output": corrected_output,
                "error_type": type(exc).__name__,
            }

        # --------------------------------------------------
        # Calculate improvement
        # --------------------------------------------------

        corrected_score = corrected_evaluation.get(
            "overall_score",
            0,
        )

        original_score = evaluation.get(
            "overall_score",
            0,
        )

        improvement = (
            corrected_score
            - original_score
        )

        # --------------------------------------------------
        # Return correction result
        # --------------------------------------------------

        return {
            "corrected": True,
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "output": corrected_output,
            "evaluation": corrected_evaluation,
            "original_evaluation": evaluation,
            "improvement": improvement,
        }