"""Single deterministic test command for AION.

Runs everything that does not require a live Gemini API key/quota:
  1. unittest discovery over tests/test_*.py
  2. the offline evaluator/auditor benchmark (fixed fixtures, no network)
  3. the correction-engine benchmark (fixed fixtures, no network)

Deliberately excludes tests/run_benchmark.py, which calls the live
Gemini API and is neither deterministic nor free to run.

Usage:
    python run_tests.py

Exit code is 0 only if unit tests pass AND both benchmarks hit 100%.
"""

import sys
import unittest

import tests.offline_benchmark as offline_benchmark
import tests.correction_benchmark as correction_benchmark


def run_unit_tests():
    print("=" * 70)
    print("UNIT TESTS (tests/test_*.py)")
    print("=" * 70)

    suite = unittest.defaultTestLoader.discover(
        start_dir="tests",
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


def main():
    results = {}

    results["unit_tests"] = run_unit_tests()

    print()
    results["offline_benchmark"] = offline_benchmark.main()

    print()
    results["correction_benchmark"] = correction_benchmark.main()

    print()
    print("=" * 70)
    print("AION TEST SUMMARY")
    print("=" * 70)

    for name, ok in results.items():
        print(f"{name:.<40} {'PASS' if ok else 'FAIL'}")

    print("=" * 70)

    overall_ok = all(results.values())
    print("OVERALL: " + ("PASS" if overall_ok else "FAIL"))

    return overall_ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
