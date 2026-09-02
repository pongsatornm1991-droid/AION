import json
import tempfile
import unittest
from pathlib import Path

from brain.curiosity_constitution import CuriosityConstitution
from brain.source_registry import SourceRegistry


class CuriosityConstitutionTests(unittest.TestCase):
    def setUp(self):
        self.constitution = CuriosityConstitution()

    def test_identity_question_is_eligible(self):
        report = self.constitution.assess("How should an AI revise a belief when evidence changes?")
        self.assertTrue(report.eligible)
        self.assertIn("identity_and_memory", report.matched_domains)

    def test_context_can_connect_an_unusual_question(self):
        report = self.constitution.assess("What makes a bridge stable?", tags=["goal"])
        self.assertTrue(report.eligible)
        self.assertGreaterEqual(report.relevance_score, 1)

    def test_thai_context_is_a_recognized_interest_not_a_constraint(self):
        report = self.constitution.assess("How is Bangkok adapting to a changing climate?")
        self.assertTrue(report.eligible)
        self.assertIn("thai_context", report.matched_domains)

    def test_novel_question_is_eligible_for_exploration(self):
        question = {"statement": "What are today’s lottery numbers?", "tags": [], "importance": 5}
        ranked = self.constitution.rank_questions([question], exploration=True)
        self.assertEqual(ranked[0][0]["statement"], question["statement"])
        self.assertEqual(ranked[0][1].relevance_score, 0)

    def test_rank_prefers_domain_connection_before_priority(self):
        questions = [
            {"statement": "What are today’s lottery numbers?", "tags": ["goal"], "importance": 5, "timestamp": "2026-01-01"},
            {"statement": "How do humans learn language?", "tags": [], "importance": 1, "timestamp": "2026-01-01"},
        ]
        ranked = self.constitution.rank_questions(questions)
        self.assertEqual(ranked[0][0]["statement"], "How do humans learn language?")

    def test_exploration_prefers_a_question_without_an_existing_connection(self):
        questions = [
            {"statement": "How do humans learn language?", "tags": [], "importance": 5, "timestamp": "2026-01-01"},
            {"statement": "What are today’s lottery numbers?", "tags": [], "importance": 1, "timestamp": "2026-01-01"},
        ]
        ranked = self.constitution.rank_questions(questions, exploration=True)
        self.assertEqual(ranked[0][0]["statement"], "What are today’s lottery numbers?")


class SourceRegistryTests(unittest.TestCase):
    def test_registry_exposes_only_enabled_source(self):
        registry = SourceRegistry()
        self.assertEqual(
            [item["id"] for item in registry.enabled_sources()],
            ["wikipedia", "youtube_discovery"],
        )

    def test_missing_registry_is_safe(self):
        registry = SourceRegistry("missing-source-registry.json")
        self.assertEqual(registry.enabled_sources(), [])

    def test_custom_registry_loads_from_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            path.write_text(json.dumps({"sources": [{"id": "x", "enabled": True}]}), encoding="utf-8")
            self.assertEqual(SourceRegistry(path).source("x")["id"], "x")
