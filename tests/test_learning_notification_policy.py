import ast
import unittest
from pathlib import Path

from brain.search_query_planner import SearchQueryPlanner
from main import _format_learning_telegram_report


class LearningNotificationPolicyTests(unittest.TestCase):
    def test_yakhchal_query_is_compacted_for_encyclopedia_search(self):
        queries = SearchQueryPlanner().plan(
            "How did ancient Persian Yakhchāl structures preserve ice?",
            "general_external",
        )
        self.assertTrue(any("yakhchal" in query for query in queries))
        self.assertNotEqual(queries[0], "How did ancient Persian Yakhchāl structures preserve ice?")

    def test_learning_telegram_notifier_only_sends_completed_learning(self):
        tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))
        function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "run_learning_cycle")
        self.assertIn("if stage == 'answered':", ast.unparse(function))

    def test_completed_learning_identifies_the_research_team(self):
        message = _format_learning_telegram_report({"stage": "answered"})
        self.assertIn("AION Research Team", message)
        self.assertIn("Evidence Analyst", message)
