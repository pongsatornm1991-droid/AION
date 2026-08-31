"""Offline tests for the read-only Instagram feedback cycle."""

import shutil
import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.social_feedback import InstagramFeedbackCycle


class InstagramFeedbackCycleTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)
        self.overview = {"username": "aion", "followers_count": 12, "media_count": 1}
        self.media = [{
            "id": "media-1", "caption": "AION เรียนรู้", "timestamp": "2026-09-01T00:00:00+0000",
            "like_count": 3, "comments_count": 1, "media_type": "IMAGE", "permalink": "https://example.test/post",
        }]
        self.cycle = InstagramFeedbackCycle(
            self.memory, lambda: self.overview, lambda limit: self.media[:limit],
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_first_capture_records_account_and_media(self):
        report = self.cycle.capture_once()

        self.assertEqual(report["stage"], "captured")
        self.assertEqual(report["recorded"], 2)
        self.assertEqual(len(self.memory.all("social_feedback")), 2)

    def test_identical_capture_does_not_spam_memory(self):
        self.cycle.capture_once()
        report = self.cycle.capture_once()

        self.assertEqual(report["stage"], "no-changes")
        self.assertEqual(report["recorded"], 0)

    def test_changed_engagement_is_recorded(self):
        self.cycle.capture_once()
        self.media[0]["like_count"] = 8

        report = self.cycle.capture_once()

        self.assertEqual(report["stage"], "captured")
        self.assertEqual(report["recorded"], 1)

    def test_fetch_failure_is_reported_without_writing_memory(self):
        failing = InstagramFeedbackCycle(
            self.memory,
            lambda: (_ for _ in ()).throw(RuntimeError("token expired")),
            lambda limit: [],
        )

        report = failing.capture_once()

        self.assertEqual(report["stage"], "fetch-failed")
        self.assertEqual(report["recorded"], 0)
