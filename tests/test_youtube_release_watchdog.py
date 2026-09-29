"""Offline regression tests for the YouTube release watchdog.

No test here makes a live network call -- fetch_runs/dispatch are always
injected fakes, matching this repo's convention for every other module
that talks to an external API (Facebook, Telegram, GitHub's own Actions
API in publish_workflow_status.py).
"""

import importlib.util
import unittest
from datetime import datetime, time, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "youtube_release_watchdog", ROOT / "tools" / "youtube_release_watchdog.py"
)
watchdog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watchdog)

# Matches core/channel_policy.json's real shorts_times (18:00/20:30 Bangkok
# == 11:00/13:30 UTC), injected explicitly so these tests stay deterministic
# regardless of the live policy file's own contents.
TWO_SLOTS_UTC = [time(11, 0), time(13, 30)]


def _run(created_at):
    return {"created_at": created_at}


class SlotWindowsTests(unittest.TestCase):
    def test_no_windows_before_the_first_slot(self):
        now = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
        self.assertEqual([], watchdog.slot_windows(TWO_SLOTS_UTC, now))

    def test_one_window_between_the_two_slots(self):
        now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        windows = watchdog.slot_windows(TWO_SLOTS_UTC, now)
        self.assertEqual(1, len(windows))
        start, end = windows[0]
        self.assertEqual(datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc), start)
        self.assertEqual(datetime(2026, 9, 29, 13, 30, tzinfo=timezone.utc), end)

    def test_two_windows_after_both_slots_the_second_bounded_by_now(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        windows = watchdog.slot_windows(TWO_SLOTS_UTC, now)
        self.assertEqual(2, len(windows))
        self.assertEqual((datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc), datetime(2026, 9, 29, 13, 30, tzinfo=timezone.utc)), windows[0])
        self.assertEqual((datetime(2026, 9, 29, 13, 30, tzinfo=timezone.utc), now), windows[1])


class TodaysAttemptExistsTests(unittest.TestCase):
    def test_true_when_a_run_was_created_within_the_only_open_slot(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-22T13:31:02Z")]
        self.assertTrue(watchdog.todays_attempt_exists(runs, now, [time(13, 30)]))

    def test_false_when_the_only_run_today_is_before_the_scheduled_hour(self):
        # e.g. a manual workflow_dispatch run earlier in the day should not
        # count as having covered today's fixed 20:30 Bangkok appointment.
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-22T02:00:00Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now, [time(13, 30)]))

    def test_false_when_the_only_run_is_from_a_prior_day(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-20T19:47:24Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now, [time(13, 30)]))

    def test_false_for_no_runs_at_all(self):
        now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
        self.assertFalse(watchdog.todays_attempt_exists([], now, [time(13, 30)]))

    def test_true_when_no_slot_has_begun_yet_today(self):
        now = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)
        self.assertTrue(watchdog.todays_attempt_exists([], now, TWO_SLOTS_UTC))

    def test_two_slots_both_covered_is_true(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-29T11:05:00Z"), _run("2026-09-29T13:32:00Z")]
        self.assertTrue(watchdog.todays_attempt_exists(runs, now, TWO_SLOTS_UTC))

    def test_only_the_first_slot_covered_is_still_false(self):
        # Regression: a single run satisfying the earlier slot must never
        # be mistaken for also covering the later, still-missed slot.
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-29T11:05:00Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now, TWO_SLOTS_UTC))

    def test_only_the_second_slot_covered_is_still_false(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        runs = [_run("2026-09-29T13:32:00Z")]
        self.assertFalse(watchdog.todays_attempt_exists(runs, now, TWO_SLOTS_UTC))


class CheckTests(unittest.TestCase):
    def test_too_early_before_the_first_scheduled_hour_never_fetches_or_dispatches(self):
        now = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)
        calls = {"fetch": 0, "dispatch": 0}

        def fetch_runs():
            calls["fetch"] += 1
            return []

        def dispatch():
            calls["dispatch"] += 1

        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs, dispatch=dispatch,
            scheduled_hours=[time(13, 30)],
        )
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
            dispatch=lambda: dispatched.append(True), scheduled_hours=[time(13, 30)],
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
            dispatch=lambda: dispatched.append(True), scheduled_hours=[time(13, 30)],
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
            dispatch=lambda: dispatched.append(True), scheduled_hours=[time(13, 30)],
        )
        self.assertEqual({"stage": "would-dispatch-missed-schedule"}, result)
        self.assertEqual([], dispatched)

    def test_dispatches_when_only_one_of_two_slots_is_missed(self):
        # Regression for the 2026-09-29 two-slots-a-day change: the first
        # slot ran fine, but the second (later) slot's own window has no
        # run in it yet -- this must still count as missed overall.
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        dispatched = []

        def fetch_runs():
            return [_run("2026-09-29T11:05:00Z")]

        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True), scheduled_hours=TWO_SLOTS_UTC,
        )
        self.assertEqual({"stage": "dispatched-missed-schedule"}, result)
        self.assertEqual([True], dispatched)

    def test_does_not_dispatch_when_both_slots_are_covered(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc)
        dispatched = []

        def fetch_runs():
            return [_run("2026-09-29T11:05:00Z"), _run("2026-09-29T13:32:00Z")]

        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True), scheduled_hours=TWO_SLOTS_UTC,
        )
        self.assertEqual({"stage": "already-attempted-today"}, result)
        self.assertEqual([], dispatched)

    def test_uses_the_real_policy_when_no_hours_are_injected(self):
        # No scheduled_hours override -- exercises the real
        # brain.channel_policy.ChannelPolicy read end to end.
        now = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)
        result = watchdog.check("owner/repo", "token", now=now, fetch_runs=lambda: [])
        self.assertEqual({"stage": "too-early"}, result)

    def test_a_different_workflow_can_be_watched_with_its_own_schedule(self):
        # Regression, 2026-09-29: thai-dub.yml's own daily 14:30 UTC cron
        # was silently dropped by GitHub the same day as the original
        # youtube-creator.yml incident -- found only because a published
        # episode had no Thai dub at all. One script must be able to
        # self-heal either workflow.
        now = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
        fetched_urls = []

        def fetch_runs():
            fetched_urls.append(True)
            return []

        dispatched = []
        result = watchdog.check(
            "owner/repo", "token", now=now, fetch_runs=fetch_runs,
            dispatch=lambda: dispatched.append(True),
            workflow_file="thai-dub.yml", scheduled_hours=[time(14, 30)],
        )
        self.assertEqual({"stage": "dispatched-missed-schedule"}, result)
        self.assertEqual([True], dispatched)
        self.assertEqual([True], fetched_urls)


class DispatchRunTests(unittest.TestCase):
    def test_sends_scheduled_recovery_input_only_for_youtube_creator(self):
        captured = {}
        real_request_cls = watchdog.Request

        def fake_request(url, method=None, data=None, headers=None):
            captured["url"] = url
            captured["data"] = data
            return real_request_cls("https://example.test")

        class FakeResponse:
            status = 204
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with mock.patch.object(watchdog, "Request", side_effect=fake_request), \
             mock.patch.object(watchdog, "urlopen", return_value=FakeResponse()):
            watchdog._dispatch_run("owner/repo", "token")
        self.assertIn("youtube-creator.yml", captured["url"])
        self.assertIn(b"scheduled_recovery", captured["data"])

    def test_sends_no_scheduled_recovery_input_for_another_workflow(self):
        # thai-dub.yml declares no such input; sending it would be
        # rejected by GitHub's dispatch API as an unknown field.
        captured = {}
        real_request_cls = watchdog.Request

        def fake_request(url, method=None, data=None, headers=None):
            captured["url"] = url
            captured["data"] = data
            return real_request_cls("https://example.test")

        class FakeResponse:
            status = 204
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with mock.patch.object(watchdog, "Request", side_effect=fake_request), \
             mock.patch.object(watchdog, "urlopen", return_value=FakeResponse()):
            watchdog._dispatch_run("owner/repo", "token", workflow_file="thai-dub.yml")
        self.assertIn("thai-dub.yml", captured["url"])
        self.assertNotIn(b"scheduled_recovery", captured["data"])
        self.assertNotIn(b"inputs", captured["data"])


class ParseScheduledHoursTests(unittest.TestCase):
    def test_parses_one_hour(self):
        self.assertEqual([time(14, 30)], watchdog._parse_scheduled_hours("14:30"))

    def test_parses_several_comma_separated_hours(self):
        self.assertEqual(
            [time(11, 0), time(13, 30)],
            watchdog._parse_scheduled_hours("11:00, 13:30"),
        )


if __name__ == "__main__":
    unittest.main()
