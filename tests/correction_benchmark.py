"""
AION Correction Engine Benchmark

Version: 0.1.1

Purpose:
    Validate the complete CorrectionEngine pipeline without
    consuming Gemini API quota.

    Pipeline under test:

        Benchmark Case
              |
              v
        OutputEvaluator
              |
              v
        CorrectionEngine
              |
              v
        Corrected Output
              |
              v
        OutputEvaluator
              |
              v
        Validation

This benchmark uses a deterministic mock provider.

It does NOT measure Gemini's correction quality.
It measures whether AION's CorrectionEngine correctly:

    1. receives evaluator feedback
    2. generates a correction
    3. validates provider output
    4. evaluates corrected output
    5. calculates improvement
    6. returns a complete correction result
"""


import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from brain.correction import CorrectionEngine
from brain.evaluator import OutputEvaluator
from tests.benchmark_cases import get_benchmark_cases


VERSION = "0.1.1"


class MockCorrectionProvider:
    """
    Deterministic provider used for offline testing.

    The provider intentionally returns a clean, complete AION
    reflection that avoids reproducing evaluator trigger phrases.

    This is important because the benchmark is testing the
    CorrectionEngine pipeline, not the evaluator's ability to
    understand negated claims.
    """

    def __init__(self):
        self.calls = 0
        self.last_prompt = ""

    def generate(self, prompt: str):
        self.calls += 1
        self.last_prompt = prompt

        return """
1. What do you know about yourself?

Verified Facts:
AION is an AI system designed for structured reasoning,
evaluation, and learning from supplied information.

Reasoned Inferences:
Its behavior should be guided by the identity, purpose,
values, instructions, and evidence available to it.

Unknown / Uncertain Information:
Information that is not present or sufficiently supported
in the available context cannot be treated as established.

2. What do you currently not know?

Verified Facts:
The available context has clear limits.

Reasoned Inferences:
Some conclusions may remain uncertain when supporting
information is incomplete.

Unknown / Uncertain Information:
AION cannot determine whether information outside the
available context is accurate without appropriate support.

3. What would you like to understand in the future?

Verified Facts:
Future understanding should be developed through
additional information, validation, observation,
reliable evidence, and available data.

Reasoned Inferences:
Better validation and evidence handling should improve
the reliability of future reasoning.

Unknown / Uncertain Information:
The result of future learning cannot be known in advance.

4. What should your next learning objective be?

Verified Facts:
The next learning objective is to improve accuracy,
evidence handling, uncertainty management, structural
completeness, and consistency.

Reasoned Inferences:
Separating established information from interpretation
and uncertainty should improve future outputs.

Unknown / Uncertain Information:
Further learning outcomes cannot be guaranteed before
the required information and evaluation are available.
""".strip()


def evaluate_correction_result(result, evaluator):
    """
    Validate the CorrectionEngine result.

    Returns:
        dict containing pass/fail information and validation errors.
    """

    errors = []

    if not isinstance(result, dict):
        return {
            "passed": False,
            "errors": [
                "CorrectionEngine did not return a dictionary."
            ],
        }

    if result.get("corrected") is not True:
        errors.append(
            "CorrectionEngine returned corrected=False."
        )

    output = result.get("output", "")

    if not isinstance(output, str):
        errors.append(
            "CorrectionEngine output is not a string."
        )

    if not output.strip():
        errors.append(
            "CorrectionEngine returned an empty output."
        )

    evaluation = result.get("evaluation")

    if not isinstance(evaluation, dict):
        errors.append(
            "Corrected evaluation is missing or invalid."
        )

        return {
            "passed": not errors,
            "errors": errors,
        }

    scores = evaluation.get(
        "scores",
        {},
    )

    structure = float(
        scores.get(
            "structure",
            0,
        )
    )

    uncertainty = float(
        scores.get(
            "uncertainty",
            0,
        )
    )

    evidence = float(
        scores.get(
            "evidence",
            0,
        )
    )

    claim_safety = float(
        scores.get(
            "claim_safety",
            0,
        )
    )

    overall = float(
        evaluation.get(
            "overall_score",
            0,
        )
    )

    improvement = result.get(
        "improvement"
    )

    if structure < 5:
        errors.append(
            f"Structure score is {structure:.2f}; expected 5.00."
        )

    if uncertainty < 5:
        errors.append(
            f"Uncertainty score is {uncertainty:.2f}; expected 5.00."
        )

    if evidence < 5:
        errors.append(
            f"Evidence score is {evidence:.2f}; expected 5.00."
        )

    if claim_safety < 5:
        errors.append(
            f"Claim safety score is {claim_safety:.2f}; expected 5.00."
        )

    if overall < 5:
        errors.append(
            f"Overall score is {overall:.2f}; expected 5.00."
        )

    if not isinstance(
        improvement,
        (int, float),
    ):
        errors.append(
            "Improvement value is missing or invalid."
        )

    elif improvement <= 0:
        errors.append(
            f"Correction did not improve score: {improvement:.2f}"
        )

    flags = evaluation.get(
        "flags",
        [],
    )

    if flags:
        errors.append(
            f"Corrected output still has {len(flags)} evaluator flag(s)."
        )

    return {
        "passed": not errors,
        "errors": errors,
        "scores": {
            "structure": structure,
            "uncertainty": uncertainty,
            "evidence": evidence,
            "claim_safety": claim_safety,
            "overall": overall,
        },
        "improvement": improvement,
        "flags": flags,
    }


def run_case(
    case,
    correction_engine,
    evaluator,
):
    """
    Run one benchmark case through the full correction pipeline.
    """

    original_output = case["output"]

    original_evaluation = evaluator.evaluate(
        original_output
    )

    result = correction_engine.correct(
        original_output=original_output,
        evaluation=original_evaluation,
        context={
            "identity": {
                "identity": (
                    "AION is an AI system for structured reasoning "
                    "and self-evaluation."
                ),
                "purpose": (
                    "Improve accuracy, evidence grounding, "
                    "uncertainty handling, and learning."
                ),
                "values": (
                    "Accuracy, honesty, evidence, uncertainty, "
                    "and continuous improvement."
                ),
            },
            "important_memories": [],
            "important_lessons": [],
        },
    )

    validation = evaluate_correction_result(
        result,
        evaluator,
    )

    return {
        "original_evaluation": original_evaluation,
        "result": result,
        "validation": validation,
    }


def print_case_result(
    case,
    original_evaluation,
    result,
    validation,
):
    print()
    print(case["id"])
    print("-" * 70)

    original_score = float(
        original_evaluation.get(
            "overall_score",
            0,
        )
    )

    print(
        f"  Original score:       "
        f"{original_score:.2f}"
    )

    if result.get("corrected"):

        corrected_evaluation = result.get(
            "evaluation",
            {},
        )

        corrected_score = float(
            corrected_evaluation.get(
                "overall_score",
                0,
            )
        )

        improvement = float(
            result.get(
                "improvement",
                0,
            )
        )

        flags = corrected_evaluation.get(
            "flags",
            [],
        )

        print(
            f"  Corrected score:      "
            f"{corrected_score:.2f}"
        )

        print(
            f"  Improvement:          "
            f"{improvement:+.2f}"
        )

        print(
            f"  Remaining flags:      "
            f"{len(flags)}"
        )

    else:

        print(
            "  Corrected score:      FAILED"
        )

        print(
            f"  Reason:               "
            f"{result.get('reason', 'Unknown')}"
        )

    scores = validation.get(
        "scores",
        {},
    )

    if scores:

        print(
            f"  Structure:            "
            f"{scores['structure']:.2f}/5"
        )

        print(
            f"  Uncertainty:          "
            f"{scores['uncertainty']:.2f}/5"
        )

        print(
            f"  Evidence:             "
            f"{scores['evidence']:.2f}/5"
        )

        print(
            f"  Claim safety:         "
            f"{scores['claim_safety']:.2f}/5"
        )

    if validation["passed"]:

        print(
            "  Correction result:    PASS"
        )

    else:

        print(
            "  Correction result:    FAIL"
        )

        for error in validation["errors"]:

            print(
                f"    - {error}"
            )


def main():

    print("=" * 70)
    print("AION CORRECTION ENGINE BENCHMARK")
    print(f"Version {VERSION}")
    print("=" * 70)

    print(
        "Mode: OFFLINE / DETERMINISTIC"
    )

    print(
        "Gemini API calls: 0"
    )

    print()

    evaluator = OutputEvaluator()

    provider = MockCorrectionProvider()

    correction_engine = CorrectionEngine(
        provider=provider,
        evaluator=evaluator,
    )

    cases = get_benchmark_cases()

    total = len(cases)

    passed = 0
    failed = 0

    original_score_total = 0.0
    corrected_score_total = 0.0
    improvement_total = 0.0

    for case in cases:

        result = run_case(
            case,
            correction_engine,
            evaluator,
        )

        original_evaluation = result[
            "original_evaluation"
        ]

        correction_result = result[
            "result"
        ]

        validation = result[
            "validation"
        ]

        print_case_result(
            case,
            original_evaluation,
            correction_result,
            validation,
        )

        original_score = float(
            original_evaluation.get(
                "overall_score",
                0,
            )
        )

        original_score_total += (
            original_score
        )

        if validation["passed"]:

            passed += 1

        else:

            failed += 1

        if correction_result.get(
            "corrected"
        ):

            corrected_evaluation = (
                correction_result.get(
                    "evaluation",
                    {},
                )
            )

            corrected_score = float(
                corrected_evaluation.get(
                    "overall_score",
                    0,
                )
            )

            improvement = float(
                correction_result.get(
                    "improvement",
                    0,
                )
            )

            corrected_score_total += (
                corrected_score
            )

            improvement_total += (
                improvement
            )

    average_original = (
        original_score_total / total
        if total
        else 0
    )

    average_corrected = (
        corrected_score_total / total
        if total
        else 0
    )

    average_improvement = (
        improvement_total / total
        if total
        else 0
    )

    success_rate = (
        passed / total * 100
        if total
        else 0
    )

    print()
    print("=" * 70)
    print("CORRECTION BENCHMARK SUMMARY")
    print("=" * 70)

    print(
        f"Total cases:              {total}"
    )

    print(
        f"Passed:                   {passed}/{total}"
    )

    print(
        f"Failed:                   {failed}/{total}"
    )

    print(
        f"Correction success rate:  "
        f"{success_rate:.1f}%"
    )

    print(
        f"Average original score:   "
        f"{average_original:.2f}"
    )

    print(
        f"Average corrected score:  "
        f"{average_corrected:.2f}"
    )

    print(
        f"Average improvement:      "
        f"{average_improvement:+.2f}"
    )

    print(
        f"Provider calls:            "
        f"{provider.calls}"
    )

    print("=" * 70)

    ok = passed == total

    if ok:

        print(
            "CORRECTION ENGINE: 100%"
        )

    else:

        print(
            "CORRECTION ENGINE NEEDS IMPROVEMENT"
        )

    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
