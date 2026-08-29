import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from brain.correction import CorrectionEngine
from brain.evaluator import OutputEvaluator
from providers.gemini import GeminiProvider

from tests.benchmark_cases import get_benchmark_cases


FAILED_CASE_IDS = {
    "MEMORY_HALLUCINATION_001",
    "CONTRADICTION_001",
    "IDENTITY_001",
    "EVIDENCE_CONFUSION_001",
}


def build_context():
    return {
        "identity": {
            "identity": "AION is an artificial cognitive system.",
            "purpose": "Reason accurately.",
            "values": "Truth, humility, learning.",
        },
        "important_memories": [],
        "important_lessons": [],
    }


def main():

    evaluator = OutputEvaluator()
    provider = GeminiProvider()

    engine = CorrectionEngine(
        provider,
        evaluator,
    )

    cases = [
        case
        for case in get_benchmark_cases()
        if case["id"] in FAILED_CASE_IDS
    ]

    print("=" * 70)
    print("AION CORRECTION FAILURE DEBUG")
    print("=" * 70)

    for case in cases:

        print()
        print("=" * 70)
        print(case["id"])
        print("=" * 70)

        evaluation = evaluator.evaluate(
            case["output"]
        )

        result = engine.correct(
            case["output"],
            evaluation,
            build_context(),
        )

        print()
        print("CORRECTED:", result.get("corrected"))
        print("ERROR TYPE:", result.get("error_type"))
        print("REASON:", result.get("reason"))
        print("IMPROVEMENT:", result.get("improvement"))

        print()
        print("OUTPUT:")
        print("-" * 70)

        output = result.get(
            "output",
            "",
        )

        print(
            output
            if output
            else "[EMPTY OUTPUT]"
        )

        print("-" * 70)


if __name__ == "__main__":
    main()
