"""
Phase 5F.5I structural regression tests.

These tests deliberately do not execute a live WebLearningCycle.
They verify the production control-flow contract via AST/source
inspection so no real curiosity-question attempt can be consumed.
"""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "brain" / "learning.py"


def _tree_and_function():
    source = LEARNING.read_text(encoding="utf-8")
    tree = ast.parse(source)

    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "research_once"
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected one research_once, found {len(matches)}"
        )

    return source, matches[0]


def _call_name(node):
    if not isinstance(node, ast.Call):
        return None

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    if isinstance(node.func, ast.Name):
        return node.func.id

    return None


class Phase5F5IContractTests(unittest.TestCase):

    def test_specialized_retrieval_uses_candidate_budget(self):
        _, fn = _tree_and_function()

        values = []

        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue

            if _call_name(node) != "_retrieve_from_adapter":
                continue

            for keyword in node.keywords:
                if keyword.arg == "max_items":
                    values.append(keyword.value)

        self.assertEqual(len(values), 1)
        self.assertIsInstance(values[0], ast.Name)
        self.assertEqual(
            values[0].id,
            "candidate_budget",
        )

    def test_candidate_budget_is_bounded_to_ten(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "target_count * 3",
            source,
        )

        self.assertIn(
            "candidate_budget = min(",
            source,
        )

        self.assertIn(
            "\n                10,\n",
            source,
        )

    def test_qualification_loop_has_early_break(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "len(new_evidence_batch)",
            source,
        )

        self.assertIn(
            ">= target_count",
            source,
        )

        self.assertIn(
            "PHASE 5F.5I — QUALIFICATION-AWARE EARLY STOP",
            source,
        )

    def test_partial_evidence_has_incomplete_stage(self):
        source, _ = _tree_and_function()

        self.assertIn(
            '"insufficient-qualifying-evidence"',
            source,
        )

        self.assertIn(
            "len(new_evidence_batch)",
            source,
        )

        self.assertIn(
            "< missing_evidence_count",
            source,
        )

    def test_partial_evidence_boundary_preserves_resume(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "not resume_from_existing_evidence",
            source,
        )

        self.assertIn(
            "not use_legacy_general_flow",
            source,
        )

    def test_existing_fidelity_contract_remains(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "source_extract",
            source,
        )

        self.assertIn(
            "EvidenceQualificationGate",
            source,
        )

    def test_existing_provider_contract_remains(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "classify_provider_error",
            source,
        )

    def test_existing_dedupe_contract_remains(self):
        source, _ = _tree_and_function()

        self.assertIn(
            "source_already_seen",
            source,
        )


if __name__ == "__main__":
    unittest.main()
