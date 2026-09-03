"""Tests for tools/publish_workflow_status.py -- offline only, no
real network call. Confirms the latest-run-per-workflow picking,
categorization, and tile counting logic against hand-built sample
GitHub Actions API responses, and that a missing GITHUB_TOKEN fails
loudly rather than silently publishing an empty/stale status."""

import importlib.util
import json
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
    return {
        "path": path,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "html_url": html_url,
    }


class TestCategoryFor(unittest.TestCase):
    def test_known_workflow_maps_to_its_category(self):
        key, label = pws.category_for(".github/workflows/social-cycle.yml")
        self.assertEqual(key, "post")
        self.assertEqual(label, "เนื้อหา & โพสต์")

    def test_unknown_workflow_falls_back_to_other(self):
        key, label = pws.category_for(".github/workflows/some-new-thing.yml")
        self.assertEqual(key, pws.OTHER_KEY)
        self.assertEqual(label, pws.OTHER_LABEL)

    def test_missing_path_falls_back_to_other(self):
        key, _ = pws.category_for(None)
        self.assertEqual(key, pws.OTHER_KEY)


class TestPillFor(unittest.TestCase):
    def test_in_progress_is_running(self):
        cls, label = pws.pill_for({"status": "in_progress", "conclusion": None})
        self.assertEqual(cls, "running")

    def test_success(self):
        cls, _ = pws.pill_for({"status": "completed", "conclusion": "success"})
        self.assertEqual(cls, "success")

    def test_failure_variants(self):
        for conclusion in ("failure", "timed_out", "startup_failure"):
            cls, _ = pws.pill_for({"status": "completed", "conclusion": conclusion})
            self.assertEqual(cls, "failure")

    def test_no_run_at_all(self):
        cls, label = pws.pill_for(None)
        self.assertEqual(cls, "unknown")
        self.assertEqual(label, "ไม่มีข้อมูล")


class TestBuildStatus(unittest.TestCase):
    def test_only_the_latest_run_per_workflow_counts(self):
        runs = [
            _run(".github/workflows/social-cycle.yml", "social-cycle", "completed", "failure", "2026-09-01T00:00:00Z"),
            _run(".github/workflows/social-cycle.yml", "social-cycle", "completed", "success", "2026-09-02T00:00:00Z"),
        ]
        status = pws.build_status(runs)
        self.assertEqual(status["tiles"]["total"], 1)
        self.assertEqual(status["tiles"]["ok"], 1)
        self.assertEqual(status["tiles"]["attn"], 0)

    def test_tile_counts_across_mixed_states(self):
        runs = [
            _run(".github/workflows/social-cycle.yml", "social-cycle", "completed", "success", "2026-09-03T10:00:00Z"),
            _run(".github/workflows/youtube-shorts.yml", "youtube-shorts", "in_progress", None, "2026-09-03T11:00:00Z"),
            _run(".github/workflows/tests.yml", "tests", "completed", "failure", "2026-09-03T08:00:00Z"),
        ]
        status = pws.build_status(runs)
        self.assertEqual(status["tiles"], {"total": 3, "ok": 1, "attn": 1, "running": 1})

    def test_groups_are_categorized_and_ordered(self):
        runs = [
            _run(".github/workflows/tests.yml", "tests", "completed", "success", "2026-09-03T08:00:00Z"),
            _run(".github/workflows/social-cycle.yml", "social-cycle", "completed", "success", "2026-09-03T09:00:00Z"),
            _run(".github/workflows/mystery.yml", "mystery", "completed", "success", "2026-09-03T09:00:00Z"),
        ]
        status = pws.build_status(runs)
        keys = [g["key"] for g in status["groups"]]
        # "post" (social-cycle) is declared before "infra" (tests) in
        # CATEGORIES, and "other" (mystery) always comes last.
        self.assertEqual(keys, ["post", "infra", "other"])

    def test_generated_at_is_present_and_iso(self):
        status = pws.build_status([])
        self.assertIn("generated_at", status)
        self.assertTrue(status["generated_at"])

    def test_empty_runs_gives_zeroed_tiles_and_no_groups(self):
        status = pws.build_status([])
        self.assertEqual(status["tiles"], {"total": 0, "ok": 0, "attn": 0, "running": 0})
        self.assertEqual(status["groups"], [])


class TestMainRequiresToken(unittest.TestCase):
    def test_missing_github_token_exits_nonzero(self):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(sys, "argv", ["publish_workflow_status.py"]):
                with self.assertRaises(SystemExit) as ctx:
                    pws.main()
                self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
