"""Offline tests for the read-only Facebook Page feedback cycle and reader."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from brain.memory import MemoryEngine
from brain.social_feedback import FacebookFeedbackCycle
from tools import facebook_insights


class FacebookFeedbackCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)
        self.overview = {"name": "AION", "fan_count": 12, "followers_count": 15}
        self.posts = [{
            "id": "page_1", "message": "AION เรียนรู้", "created_time": "2026-09-01T00:00:00+0000",
            "permalink_url": "https://facebook.test/1", "reactions": 3, "comments": 1, "shares": 0,
        }]
        self.cycle = FacebookFeedbackCycle(self.memory, lambda: self.overview, lambda limit: self.posts[:limit])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_first_capture_records_page_and_post(self):
        report = self.cycle.capture_once()
        self.assertEqual("captured", report["stage"])
        self.assertEqual(2, report["recorded"])
        kinds = sorted(json.loads(entry["content"])["kind"] for entry in self.memory.all("social_feedback"))
        self.assertEqual(["facebook-page", "facebook-post"], kinds)

    def test_identical_capture_does_not_spam_memory(self):
        self.cycle.capture_once()
        report = self.cycle.capture_once()
        self.assertEqual("no-changes", report["stage"])
        self.assertEqual(0, report["recorded"])
        self.assertEqual(2, len(self.memory.all("social_feedback")))

    def test_a_changed_counter_is_recorded_once(self):
        self.cycle.capture_once()
        self.posts[0]["reactions"] = 9
        self.assertEqual(1, self.cycle.capture_once()["recorded"])
        self.assertEqual(0, self.cycle.capture_once()["recorded"])

    def test_facebook_snapshots_are_never_mistaken_for_instagram_ones(self):
        # growth / growth_pulse / dashboard key on kind == "account"/"media".
        self.cycle.capture_once()
        for entry in self.memory.all("social_feedback"):
            self.assertNotIn(json.loads(entry["content"])["kind"], ("account", "media"))
            self.assertEqual("facebook-feedback", entry["source"])

    def test_a_failed_read_is_reported_not_raised_and_records_nothing(self):
        def broken():
            raise RuntimeError("(#10) pages_read_engagement permission missing")

        report = FacebookFeedbackCycle(self.memory, broken, lambda limit: []).capture_once()
        self.assertEqual("fetch-failed", report["stage"])
        self.assertIn("pages_read_engagement", report["error"])
        self.assertEqual(0, len(self.memory.all("social_feedback")))


class FacebookInsightsReaderTests(unittest.TestCase):
    ENV = {"FACEBOOK_PAGE_ACCESS_TOKEN": "tok", "FACEBOOK_PAGE_ID": "123"}

    class _Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def test_recent_posts_are_flattened_to_plain_counters(self):
        payload = {"data": [{
            "id": "123_1", "message": "hello", "created_time": "t", "permalink_url": "u",
            "reactions": {"summary": {"total_count": 7}},
            "comments": {"summary": {"total_count": 2}},
            "shares": {"count": 4},
        }, {"id": "123_2"}]}
        with mock.patch.dict(os.environ, self.ENV), \
             mock.patch("requests.get", return_value=self._Response(payload)) as get:
            posts = facebook_insights.get_recent_posts(limit=5)
        self.assertEqual({"reactions": 7, "comments": 2, "shares": 4}, {k: posts[0][k] for k in ("reactions", "comments", "shares")})
        self.assertEqual({"reactions": 0, "comments": 0, "shares": 0}, {k: posts[1][k] for k in ("reactions", "comments", "shares")})
        self.assertTrue(get.call_args.args[0].endswith("/123/posts"))
        self.assertEqual(5, get.call_args.kwargs["params"]["limit"])

    def test_overview_reads_fans_and_followers(self):
        payload = {"name": "AION", "fan_count": 3, "followers_count": 5}
        with mock.patch.dict(os.environ, self.ENV), mock.patch("requests.get", return_value=self._Response(payload)):
            self.assertEqual(payload, facebook_insights.get_page_overview())

    def test_a_graph_error_is_raised_never_recorded_as_zeros(self):
        error = {"error": {"message": "Missing permission", "code": 10}}
        response = self._Response(error)
        response.status_code = 400
        with mock.patch.dict(os.environ, self.ENV), mock.patch("requests.get", return_value=response):
            with self.assertRaises(Exception):
                facebook_insights.get_page_overview()

    def test_limit_must_be_a_positive_integer(self):
        with mock.patch.dict(os.environ, self.ENV):
            for bad in (0, -1, True, "5"):
                with self.assertRaises(ValueError):
                    facebook_insights.get_recent_posts(limit=bad)


if __name__ == "__main__":
    unittest.main()
