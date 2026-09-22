"""Offline regression tests for the YouTube release watchdog.

No test here makes a live network call -- fetch_runs/dispatch are always
injected fakes, matching this repo's convention for every other module
that talks to an external API (Facebook, Telegram, GitHub's own Actions
API in publish_workflow_status.py).
"""

import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "youtube_release_watchdog", ROOT / "tools" / "youtube_release_watchdog.py"
)
watchdog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watchdog)


def _run(created_at):
    return {"created_at": created_at}


class TodaysAttemptExistsTests(unittest.TestCase):
    def test_true_when_a_run_was_created_today_after_the_scheduled_hour(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-22T13:31:02Z")]
        self.assertTrue(watchdog.todays_attempt_exists(runs, now))

    def test_false_when_the_only_run_today_is_before_the_scheduled_hour(self):
        # e.g. a manual workflow_dispatch run earlier in the day should not
        # count as having covered today's fixed 20:30 Bangkok appointment.
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-22T02:00:00Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now))

    def test_false_when_the_only_run_is_from_a_prior_day(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-20T19:47:24Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now))

    def test_false_for_no_runs_at_all(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        self.assertFalse(watchdog.todays_attempt_exists([], now))


class CheckTests(unittest.TestCase):
    def test_too_early_before_the_scheduled_hour_never_fetches_or_dispatches(self):
        now = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)
        calls = {"fetch": 0, "dispatch": 0}

        def fetch_runs():
            calls["fetch"] += 1
            return []

        def dispatch():
            calls["dispatch"] += 1

        result = watchdog.check("owner/repo", "token", now=now, fetch_runs=fetch_runs, dispatch=dispatch)
        self.assertEqual({"stage": "too-early"}, result)
        self.assertEqual(0, calls["fetch"])
        self.assertEqual(0, calls["dispatch"])

    def test_does_not_dispatch_when_todays_run_already_exists(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        dispatched = []

        def fetch_runs():
            return [_run("2026-09-22T13:30:05Z")]

        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True),
        )
        self.assertEqual({"stage": "already-attempted-today"}, result)
        self.assertEqual([], dispatched)

    def test_dispatches_when_no_run_exists_yet_today(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        dispatched = []

        def fetch_runs():
            return [_run("2026-09-20T19:47:24Z")]

        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True),
        )
        self.assertEqual({"stage": "dispatched-missed-schedule"}, result)
        self.assertEqual([True], dispatched)

    def test_dry_run_reports_without_dispatching(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        dispatched = []

        def fetch_runs():
            return []

        result = watchdog.check(
            "owner/repo", "token", now=now, dry_run=True, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True),
        )
        self.assertEqual({"stage": "would-dispatch-missed-schedule"}, result)
        self.assertEqual([], dispatched)


if __name__ == "__main__":
    unittest.main()
