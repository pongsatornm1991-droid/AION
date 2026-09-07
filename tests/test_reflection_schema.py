"""Tests for the reflection uncertainty schema and meta-loop filter."""

import unittest

from brain.evaluator import OutputEvaluator
from brain.correction import CorrectionEngine
from brain.reflection_schema import (
    ReflectionSchemaEvaluator,
    ReflectionSchemaValidator,
    filter_meta_reflection_entries,
)


VALID_REFLECTION = """1. What do you know about yourself?
Verified facts: I am a software system operating from supplied context.

2. What do you currently not know?
Unknown Facts: I do not know whether the next external task will succeed.
Cognitive Uncertainties: I cannot verify whether my current reasoning omitted a relevant alternative.

3. What would you like to understand in the future?
I would like additional evidence about real task outcomes.

4. What should your next learning objective be?
Test one bounded task and compare the result with the stated criteria.
"""


class _SpyEvaluator:
    def __init__(self):
        self.calls = []

    def evaluate(self, text):
        self.calls.append(text)
        return {
            "overall_score": 3.5,
            "scores": {
                "structure": 5,
                "uncertainty": 2,
                "evidence": 2,
                "claim_safety": 5,
            },
            "flags": [],
            "length": len(text),
        }


class _FixedProvider:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class ReflectionSchemaTests(unittest.TestCase):
    def test_valid_schema_separates_both_uncertainty_types(self):
        result = ReflectionSchemaValidator.validate(VALID_REFLECTION)
        self.assertTrue(result["valid"])
        self.assertIn("next external task", result["unknown_facts"])
        self.assertIn("reasoning", result["cognitive_uncertainties"])

    def test_missing_bucket_is_rejected_before_general_evaluator(self):
        spy = _SpyEvaluator()
        evaluator = ReflectionSchemaEvaluator(spy)
        text = VALID_REFLECTION.replace(
            "Cognitive Uncertainties:",
            "Other limitations:",
        )

        result = evaluator.evaluate(text)

        self.assertEqual(spy.calls, [])
        self.assertEqual(result["scores"]["uncertainty"], 0)
        self.assertIn(
            "Missing Cognitive Uncertainties subsection.",
            result["flags"],
        )

    def test_valid_schema_stabilizes_reflection_uncertainty_score(self):
        spy = _SpyEvaluator()
        result = ReflectionSchemaEvaluator(spy).evaluate(VALID_REFLECTION)

        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(result["scores"]["uncertainty"], 5)
        self.assertEqual(result["overall_score"], 4.25)

    def test_valid_schema_integrates_with_real_output_evaluator(self):
        result = ReflectionSchemaEvaluator(OutputEvaluator()).evaluate(
            VALID_REFLECTION
        )
        self.assertTrue(result["reflection_schema"]["valid"])
        self.assertEqual(result["scores"]["uncertainty"], 5)

    def test_meta_reflection_context_is_removed(self):
        entries = [
            {"source": "evaluator", "content": "Uncertainty score: 3"},
            {"source": "aion", "content": "AION reflection:\nold text"},
            {"source": "human", "content": "A new external task result"},
        ]
        self.assertEqual(
            filter_meta_reflection_entries(entries),
            [entries[2]],
        )

    def test_correction_pipeline_rechecks_schema_before_accepting(self):
        evaluator = ReflectionSchemaEvaluator(OutputEvaluator())
        invalid = VALID_REFLECTION.replace(
            "Cognitive Uncertainties:",
            "Other limitations:",
        )
        initial_evaluation = evaluator.evaluate(invalid)
        provider = _FixedProvider(VALID_REFLECTION)

        result = CorrectionEngine(provider, evaluator).correct(
            original_output=invalid,
            evaluation=initial_evaluation,
            context={
                "identity": {},
                "important_memories": [],
                "important_lessons": [],
            },
        )

        self.assertTrue(result["corrected"])
        self.assertTrue(result["evaluation"]["reflection_schema"]["valid"])
        self.assertGreater(result["improvement"], 0)
        self.assertIn("Cognitive Uncertainties", provider.calls[0])


if __name__ == "__main__":
    unittest.main()
