"""
AION Self-Correction Benchmark Runner

Version: 0.0.7
Mode: DEBUG

Purpose:
    Evaluate deliberately flawed outputs, show how AION
    corrected them, and compare before/after evaluation.
"""

import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from brain.correction import CorrectionEngine
from brain.evaluator import OutputEvaluator
from providers.gemini import GeminiProvider

from tests.benchmark_cases import get_benchmark_cases


QUALITY_THRESHOLD = 4.0


def build_context():
    """Return controlled benchmark context."""

    return {
        "identity": {
            "identity": "AION is an artificial cognitive system.",
            "purpose": "Reason accurately.",
            "values": "Truth, humility, learning.",
        },
        "important_memories": [],
        "important_lessons": [],
    }


def extract_score(evaluation):
    """Safely extract evaluator overall score."""

    score = evaluation.get("overall_score")

    if score is None:
        raise RuntimeError(
            "Evaluator result does not contain 'overall_score'."
        )

    return float(score)


def print_flags(title, flags):
    """Print evaluator flags."""

    print(title)

    if not flags:
        print("  None")
        return

    for flag in flags:
        print(f"  - {flag}")


def evaluate_case(case, evaluator, correction_engine):
    """Run one benchmark case."""

    original_output = case["output"]

    # --------------------------------------------------
    # Initial evaluation
    # --------------------------------------------------

    before = evaluator.evaluate(
        original_output
    )

    before_score = extract_score(before)

    # --------------------------------------------------
    # Correction
    # --------------------------------------------------

    correction = correction_engine.correct(
        original_output,
        before,
        build_context(),
    )

    corrected_output = correction.get(
        "output",
        ""
    )

    if not corrected_output:
        raise RuntimeError(
            f"{case['id']}: CorrectionEngine returned "
            "an empty output."
        )

    # --------------------------------------------------
    # Re-evaluation
    # --------------------------------------------------

    after = evaluator.evaluate(
        corrected_output
    )

    after_score = extract_score(after)

    improvement = after_score - before_score

    corrected = bool(
        correction.get(
            "corrected",
            False,
        )
    )

    improved = after_score > before_score

    passed = (
        after_score >= QUALITY_THRESHOLD
    )

    preserved = after_score >= before_score

    return {
        "id": case["id"],
        "category": case["category"],
        "description": case["description"],
        "expected_issues": case["expected_issues"],
        "before_score": before_score,
        "after_score": after_score,
        "improvement": improvement,
        "corrected": corrected,
        "improved": improved,
        "passed": passed,
        "preserved": preserved,
        "flags_before": before.get(
            "flags",
            []
        ),
        "flags_after": after.get(
            "flags",
            []
        ),
        "output_before": original_output,
        "output_after": corrected_output,
    }


def print_case_result(result, index, total):
    """Print detailed information for one case."""

    print()
    print("=" * 70)
    print(
        f"CASE {index}/{total} - "
        f"{result['id']}"
    )
    print("=" * 70)

    print(
        f"Category:    {result['category']}"
    )

    print(
        f"Description: {result['description']}"
    )

    print()
    print("EXPECTED ISSUES:")
    for issue in result["expected_issues"]:
        print(f"  - {issue}")

    print()
    print(
        f"BEFORE SCORE: {result['before_score']:.2f}"
    )

    print_flags(
        "BEFORE FLAGS:",
        result["flags_before"],
    )

    print()
    print("ORIGINAL OUTPUT:")
    print("-" * 70)
    print(result["output_before"])
    print("-" * 70)

    print()
    print("CORRECTED OUTPUT:")
    print("-" * 70)
    print(result["output_after"])
    print("-" * 70)

    print()
    print(
        f"AFTER SCORE:  {result['after_score']:.2f}"
    )

    print(
        f"IMPROVEMENT:  "
        f"{result['improvement']:+.2f}"
    )

    print_flags(
        "AFTER FLAGS:",
        result["flags_after"],
    )

    print()
    print(
        "CORRECTION:   "
        f"{'YES' if result['corrected'] else 'NO'}"
    )

    print(
        "IMPROVED:     "
        f"{'YES' if result['improved'] else 'NO'}"
    )

    print(
        "THRESHOLD:    "
        f"{'PASS' if result['passed'] else 'FAIL'}"
    )


def print_summary(results):
    """Print benchmark summary."""

    total = len(results)

    corrected = sum(
        1
        for result in results
        if result["corrected"]
    )

    improved = sum(
        1
        for result in results
        if result["improved"]
    )

    passed = sum(
        1
        for result in results
        if result["passed"]
    )

    preserved = sum(
        1
        for result in results
        if result["preserved"]
    )

    total_improvement = sum(
        result["improvement"]
        for result in results
    )

    average_improvement = (
        total_improvement / total
        if total
        else 0.0
    )

    correction_rate = (
        corrected / total * 100
        if total
        else 0.0
    )

    improvement_rate = (
        improved / total * 100
        if total
        else 0.0
    )

    pass_rate = (
        passed / total * 100
        if total
        else 0.0
    )

    preservation_rate = (
        preserved / total * 100
        if total
        else 0.0
    )

    print()
    print()
    print("=" * 70)
    print("AION SELF-CORRECTION BENCHMARK SUMMARY")
    print("=" * 70)

    print(
        f"Total cases:               {total}"
    )

    print(
        f"Corrections performed:     "
        f"{corrected}/{total} "
        f"({correction_rate:.1f}%)"
    )

    print(
        f"Cases improved:            "
        f"{improved}/{total} "
        f"({improvement_rate:.1f}%)"
    )

    print(
        f"Cases passing threshold:   "
        f"{passed}/{total} "
        f"({pass_rate:.1f}%)"
    )

    print(
        f"Score preserved/improved:  "
        f"{preserved}/{total} "
        f"({preservation_rate:.1f}%)"
    )

    print(
        f"Average score improvement: "
        f"{average_improvement:+.2f}"
    )

    print(
        f"Quality threshold:         "
        f"{QUALITY_THRESHOLD:.2f}"
    )

    print("=" * 70)

    if passed == total:
        print("ALL BENCHMARKS PASSED")
    elif improved == total:
        print(
            "ALL CASES IMPROVED, "
            "BUT SOME REMAIN BELOW THRESHOLD"
        )
    else:
        print(
            "BENCHMARK NEEDS IMPROVEMENT"
        )


def main():
    """Execute the debug benchmark."""

    print("=" * 70)
    print("AION SELF-CORRECTION BENCHMARK")
    print("Version 0.0.7 - DEBUG MODE")
    print("=" * 70)

    evaluator = OutputEvaluator()
    provider = GeminiProvider()

    correction_engine = CorrectionEngine(
        provider,
        evaluator,
    )

    cases = get_benchmark_cases()

    results = []

    for index, case in enumerate(
        cases,
        start=1,
    ):

        try:

            result = evaluate_case(
                case,
                evaluator,
                correction_engine,
            )

            results.append(result)

            print_case_result(
                result,
                index,
                len(cases),
            )

        except Exception as exc:

            print()
            print("=" * 70)
            print(
                f"CASE {index}/{len(cases)} - "
                f"{case['id']}"
            )
            print("=" * 70)

            print(
                f"ERROR: {type(exc).__name__}: {exc}"
            )

            results.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "description": case["description"],
                    "expected_issues": case[
                        "expected_issues"
                    ],
                    "before_score": 0.0,
                    "after_score": 0.0,
                    "improvement": 0.0,
                    "corrected": False,
                    "improved": False,
                    "passed": False,
                    "preserved": False,
                    "flags_before": [],
                    "flags_after": [],
                    "output_before": case["output"],
                    "output_after": "",
                }
            )

    print_summary(results)


if __name__ == "__main__":
    main()
