"""
Phase 5F.5J — Criteria-Scoped Synthesis tests.

No network.
No provider call.
No live learning cycle.
"""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "brain" / "learning.py"


def _source_tree():
    source = LEARNING.read_text(
        encoding="utf-8"
    )
    return source, ast.parse(source)


def _class(tree, name):
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == name
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected one class {name}, "
            f"found {len(matches)}"
        )

    return matches[0]


def _method(class_node, name):
    matches = [
        node
        for node in class_node.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == name
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected one method {name}, "
            f"found {len(matches)}"
        )

    return matches[0]


def _function(tree, name):
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == name
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected one function {name}, "
            f"found {len(matches)}"
        )

    return matches[0]


def _args(fn):
    values = []

    values.extend(
        getattr(
            fn.args,
            "posonlyargs",
            [],
        )
    )

    values.extend(
        fn.args.args
    )

    values.extend(
        fn.args.kwonlyargs
    )

    return [
        item.arg
        for item in values
    ]


def _call_name(node):
    if not isinstance(node, ast.Call):
        return None

    if isinstance(
        node.func,
        ast.Attribute,
    ):
        return node.func.attr

    if isinstance(
        node.func,
        ast.Name,
    ):
        return node.func.id

    return None


class Phase5F5JTests(unittest.TestCase):

    def test_build_prompt_accepts_completion_criteria(self):
        _, tree = _source_tree()

        generator = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(
                    item,
                    ast.FunctionDef,
                )
                and item.name
                == "_build_synthesis_prompt"
                for item in node.body
            )
        )

        fn = _method(
            generator,
            "_build_synthesis_prompt",
        )

        self.assertIn(
            "completion_criteria",
            _args(fn),
        )

    def test_synthesize_accepts_completion_criteria(self):
        _, tree = _source_tree()

        generator = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(
                    item,
                    ast.FunctionDef,
                )
                and item.name
                == "synthesize_answer"
                for item in node.body
            )
        )

        fn = _method(
            generator,
            "synthesize_answer",
        )

        self.assertIn(
            "completion_criteria",
            _args(fn),
        )

    def test_synthesize_passes_criteria_to_prompt(self):
        _, tree = _source_tree()

        generator = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(
                    item,
                    ast.FunctionDef,
                )
                and item.name
                == "synthesize_answer"
                for item in node.body
            )
        )

        fn = _method(
            generator,
            "synthesize_answer",
        )

        calls = [
            node
            for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and _call_name(node)
            == "_build_synthesis_prompt"
        ]

        self.assertEqual(
            len(calls),
            1,
        )

        criteria_keywords = [
            keyword
            for keyword in calls[0].keywords
            if keyword.arg
            == "completion_criteria"
        ]

        self.assertEqual(
            len(criteria_keywords),
            1,
        )

    def test_research_once_passes_completion_criteria(self):
        _, tree = _source_tree()

        fn = _function(
            tree,
            "research_once",
        )

        calls = [
            node
            for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and _call_name(node)
            == "synthesize_answer"
        ]

        self.assertEqual(
            len(calls),
            1,
        )

        criteria_keywords = [
            keyword
            for keyword in calls[0].keywords
            if keyword.arg
            == "completion_criteria"
        ]

        self.assertEqual(
            len(criteria_keywords),
            1,
        )

        value = (
            criteria_keywords[0].value
        )

        self.assertIsInstance(
            value,
            ast.Name,
        )

        self.assertEqual(
            value.id,
            "completion_criteria",
        )

    def test_old_broad_incomplete_rule_removed(self):
        source, _ = _source_tree()

        self.assertNotIn(
            "If the combined evidence is incomplete, "
            "say so clearly.",
            source,
        )

    def test_prompt_is_explicitly_criteria_scoped(self):
        source, _ = _source_tree()

        self.assertIn(
            "COMPLETION-SCOPE RULES:",
            source,
        )

        self.assertIn(
            "Do not invent additional "
            "completion requirements.",
            source,
        )

        self.assertIn(
            "EXPLICIT COMPLETION CRITERIA:",
            source,
        )

    def test_completion_evaluator_remains_conservative(self):
        source, tree = _source_tree()

        evaluator = _class(
            tree,
            "CompletionCriteriaEvaluator",
        )

        evaluator_source = (
            ast.get_source_segment(
                source,
                evaluator,
            )
        )

        self.assertIn(
            "Every explicit requirement",
            evaluator_source,
        )

        self.assertIn(
            "Do not count one source multiple times.",
            evaluator_source,
        )

        self.assertIn(
            "If the evidence only partially "
            "satisfies the criteria",
            evaluator_source,
        )

        self.assertIn(
            "Only return YES",
            evaluator_source,
        )

    def test_phase5f5i_contract_remains(self):
        source, _ = _source_tree()

        self.assertIn(
            "candidate_budget",
            source,
        )

        self.assertIn(
            "insufficient-qualifying-evidence",
            source,
        )

    def test_existing_safety_rules_remain(self):
        source, _ = _source_tree()

        self.assertIn(
            "Never claim that AION is literally conscious.",
            source,
        )

        self.assertIn(
            "Never claim that AION genuinely feels emotions.",
            source,
        )

        self.assertIn(
            "Never claim that AION personally "
            "experienced real-world events.",
            source,
        )


if __name__ == "__main__":
    unittest.main()
