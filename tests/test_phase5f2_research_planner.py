import unittest

from brain.learning import WebLearningCycle
from brain.research_planner import AutonomousResearchPlanner


class FakeRegistry:
    def __init__(self):
        self._sources = [
            {
                "id": "wikipedia",
                "name": "Wikipedia",
                "tier": "B",
                "enabled": True,
                "capabilities": [
                    "general_external",
                ],
            },
            {
                "id": "arxiv",
                "name": "arXiv",
                "tier": "A",
                "enabled": True,
                "capabilities": [
                    "general_external",
                    "research_paper",
                ],
            },
            {
                "id": "hacker_news",
                "name": "Hacker News",
                "tier": "C",
                "enabled": True,
                "capabilities": [
                    "human_perspective",
                ],
            },
        ]

    def enabled_sources(self):
        return [
            item
            for item in self._sources
            if item.get("enabled")
        ]

    def source(self, source_id):
        for item in self._sources:
            if item.get("id") == source_id:
                return item
        return None


class FakeEvidenceStore:
    def source_already_seen(
        self,
        root_question_id,
        source_kind,
        title,
        url,
    ):
        return False


class ResearchPlannerPhase5F2Tests(
    unittest.TestCase
):
    def test_planner_selects_hacker_news_for_human_perspective(self):
        planner = AutonomousResearchPlanner(
            FakeRegistry()
        )

        plan = planner.plan(
            {
                "evidence_types": [
                    "human_perspective"
                ],
                "required_count": 3,
            },
            available_adapter_ids=[
                "wikipedia",
                "arxiv",
                "hacker_news",
            ],
            existing_evidence=[],
        )

        self.assertEqual(
            plan["status"],
            "ready",
        )

        self.assertEqual(
            plan["source_id"],
            "hacker_news",
        )

        self.assertEqual(
            plan["missing_evidence_count"],
            3,
        )

    def test_capability_report_uses_registry_not_old_hardcoded_map(self):
        cycle = object.__new__(
            WebLearningCycle
        )

        cycle.source_registry = (
            FakeRegistry()
        )

        cycle.research_planner = (
            AutonomousResearchPlanner(
                cycle.source_registry
            )
        )

        cycle.adapters = {
            "hacker_news": {
                "search": lambda q: [],
                "fetch": lambda item_id: {},
            },
        }

        report = cycle._capability_report(
            {
                "evidence_types": [
                    "human_perspective"
                ],
                "required_count": 3,
            },
            existing_evidence=[],
        )

        self.assertTrue(
            report[
                "satisfiable_with_current_adapters"
            ]
        )

        self.assertEqual(
            report[
                "research_plan"
            ]["source_id"],
            "hacker_news",
        )

    def test_generic_adapter_can_collect_three_unique_items(self):
        cycle = object.__new__(
            WebLearningCycle
        )

        cycle.source_registry = (
            FakeRegistry()
        )

        cycle.evidence_store = (
            FakeEvidenceStore()
        )

        def search_fn(query, limit=10):
            return [
                {
                    "title": "101",
                    "url": "https://news.ycombinator.com/item?id=101",
                },
                {
                    "title": "102",
                    "url": "https://news.ycombinator.com/item?id=102",
                },
                {
                    "title": "103",
                    "url": "https://news.ycombinator.com/item?id=103",
                },
                {
                    "title": "104",
                    "url": "https://news.ycombinator.com/item?id=104",
                },
            ]

        def fetch_fn(item_id):
            return {
                "title": (
                    f"Human perspective {item_id}"
                ),
                "url": (
                    "https://news.ycombinator.com/"
                    f"item?id={item_id}"
                ),
                "extract": (
                    "A traceable public human "
                    f"perspective from user {item_id}."
                ),
            }

        cycle.adapters = {
            "hacker_news": {
                "search": search_fn,
                "fetch": fetch_fn,
            },
        }

        report = (
            cycle._retrieve_from_adapter(
                "hacker_news",
                "What can an AI learn from people?",
                "root-question",
                max_items=3,
            )
        )

        self.assertTrue(
            report["ok"]
        )

        self.assertEqual(
            len(report["items"]),
            3,
        )

        urls = {
            item["source"]["url"]
            for item in report["items"]
        }

        self.assertEqual(
            len(urls),
            3,
        )


if __name__ == "__main__":
    unittest.main()
