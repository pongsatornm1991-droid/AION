"""Offline regression tests for the public workflow-health publisher."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_workflow_status", ROOT / "tools" / "publish_workflow_status.py"
)
pws = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pws)


def _run(path, name, status, conclusion, created_at, html_url="https://example/run"):
    return {"path": path, "name": name, "status": status, "conclusion": conclusion,
            "created_at": created_at, "html_url": html_url}


class TestCategoryFor(unittest.TestCase):
    def test_known_workflow_maps_to_its_category(self):
        self.assertEqual("post", pws.category_for(".github/workflows/social-cycle.yml")[0])

    def test_unknown_workflow_falls_back_to_other(self):
        self.assertEqual(pws.OTHER_KEY, pws.category_for(".github/workflows/new.yml")[0])

    def test_missing_path_falls_back_to_other(self):
        self.assertEqual(pws.OTHER_KEY, pws.category_for(None)[0])


class TestPillFor(unittest.TestCase):
    def test_in_progress_is_running(self):
        self.assertEqual("running", pws.pill_for({"status": "in_progress", "conclusion": None})[0])

    def test_success(self):
        self.assertEqual("success", pws.pill_for({"status": "completed", "conclusion": "success"})[0])

    def test_failure_variants(self):
        for conclusion in ("failure", "timed_out", "startup_failure"):
            self.assertEqual("failure", pws.pill_for({"status": "completed", "conclusion": conclusion})[0])

    def test_no_run_at_all(self):
        self.assertEqual(("unknown", "ไม่มีข้อมูล"), pws.pill_for(None))


class WorkflowStatusTests(unittest.TestCase):
    def test_skipped_monitor_is_a_healthy_noop(self):
        self.assertEqual(
            ("success", "ไม่มีเหตุให้ดำเนินการ"),
            pws.pill_for({"status": "completed", "conclusion": "skipped"}),
        )

    def test_failed_workflow_remains_attention_worthy(self):
        self.assertEqual(
            ("failure", "ล้มเหลว"),
            pws.pill_for({"status": "completed", "conclusion": "failure"}),
        )


class TestBuildStatus(unittest.TestCase):
    def test_only_latest_run_per_workflow_counts(self):
        status = pws.build_status([
            _run(".github/workflows/social-cycle.yml", "social", "completed", "failure", "2026-09-01T00:00:00Z"),
            _run(".github/workflows/social-cycle.yml", "social", "completed", "success", "2026-09-02T00:00:00Z"),
        ])
        self.assertEqual({"total": 1, "ok": 1, "attn": 0, "running": 0}, status["tiles"])

    def test_tile_counts_across_mixed_states(self):
        status = pws.build_status([
            _run(".github/workflows/social-cycle.yml", "social", "completed", "success", "2026-09-03T10:00:00Z"),
            _run(".github/workflows/youtube-shorts.yml", "shorts", "in_progress", None, "2026-09-03T11:00:00Z"),
            _run(".github/workflows/tests.yml", "tests", "completed", "failure", "2026-09-03T08:00:00Z"),
        ])
        self.assertEqual({"total": 3, "ok": 1, "attn": 1, "running": 1}, status["tiles"])

    def test_groups_are_categorized_and_ordered(self):
        status = pws.build_status([
            _run(".github/workflows/tests.yml", "tests", "completed", "success", "2026-09-03T08:00:00Z"),
            _run(".github/workflows/social-cycle.yml", "social", "completed", "success", "2026-09-03T09:00:00Z"),
            _run(".github/workflows/mystery.yml", "mystery", "completed", "success", "2026-09-03T09:00:00Z"),
        ])
        self.assertEqual(["post", "infra", "other"], [group["key"] for group in status["groups"]])

    def test_empty_runs_gives_zeroed_tiles_and_no_groups(self):
        status = pws.build_status([])
        self.assertEqual({"total": 0, "ok": 0, "attn": 0, "running": 0}, status["tiles"])
        self.assertEqual([], status["groups"])


class TestMainRequiresToken(unittest.TestCase):
    def test_missing_github_token_exits_nonzero(self):
        env = {key: value for key, value in os.environ.items() if key != "GITHUB_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(sys, "argv", ["publish_workflow_status.py"]):
                with self.assertRaises(SystemExit) as ctx:
                    pws.main()
                self.assertNotEqual(0, ctx.exception.code)
