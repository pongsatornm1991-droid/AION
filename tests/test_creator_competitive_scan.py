"""Offline tests for tools/creator_competitive_scan.py.

Mocks tools.youtube_discovery entirely -- this suite must never make a live
call to the YouTube Data API, per the project's rule that unit tests never
depend on a live external service.
"""

import unittest
from unittest import mock

from tools.creator_competitive_scan import scan_niche, scan_report


SEARCH_HITS = {
    "topic a": [
        {"video_id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "Video One",
         "channel": "Channel A", "published_at": "2026-01-01T00:00:00Z", "description": ""},
    ],
    "topic b": [
        {"video_id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "Video Two",
         "channel": "Channel B", "published_at": "2026-01-02T00:00:00Z", "description": ""},
    ],
}

STATS = {
    "vid1": {"video_id": "vid1", "title": "Video One", "published_at": "2026-01-01T00:00:00Z",
             "view_count": "100", "like_count": "1", "comment_count": "0"},
    "vid2": {"video_id": "vid2", "title": "Video Two", "published_at": "2026-01-02T00:00:00Z",
             "view_count": "5000", "like_count": "2", "comment_count": "1"},
}


def fake_search(query, limit=5, api_key=None):
    return SEARCH_HITS.get(query, [])


def fake_stats(video_ids, api_key=None):
    return [STATS[video_id] for video_id in video_ids if video_id in STATS]


class ScanNicheTests(unittest.TestCase):
    def test_ranks_hits_by_view_count_descending_across_queries(self):
        with mock.patch("tools.creator_competitive_scan.search_youtube_videos", side_effect=fake_search), \
             mock.patch("tools.creator_competitive_scan.get_youtube_video_statistics", side_effect=fake_stats):
            results = scan_niche(queries=["topic a", "topic b"])
        self.assertEqual([item["video_id"] for item in results], ["vid2", "vid1"])
        self.assertEqual(results[0]["view_count"], 5000)
        self.assertEqual(results[0]["query"], "topic b")

    def test_missing_statistics_default_to_zero_views_not_a_crash(self):
        with mock.patch("tools.creator_competitive_scan.search_youtube_videos", side_effect=fake_search), \
             mock.patch("tools.creator_competitive_scan.get_youtube_video_statistics", return_value=[]):
            results = scan_niche(queries=["topic a"])
        self.assertEqual(results[0]["view_count"], 0)

    def test_propagates_provider_errors_to_the_caller(self):
        with mock.patch("tools.creator_competitive_scan.search_youtube_videos", side_effect=RuntimeError("no api key")):
            with self.assertRaises(RuntimeError):
                scan_niche(queries=["topic a"])


class ScanReportTests(unittest.TestCase):
    def test_report_never_raises_on_a_provider_failure(self):
        with mock.patch("tools.creator_competitive_scan.search_youtube_videos", side_effect=RuntimeError("boom")):
            report = scan_report(queries=["topic a"])
        self.assertFalse(report["ok"])
        self.assertEqual(report["error"], "boom")
        self.assertEqual(report["results"], [])
        self.assertIn("generated_at", report)

    def test_report_carries_ranked_results_on_success(self):
        with mock.patch("tools.creator_competitive_scan.search_youtube_videos", side_effect=fake_search), \
             mock.patch("tools.creator_competitive_scan.get_youtube_video_statistics", side_effect=fake_stats):
            report = scan_report(queries=["topic a", "topic b"])
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["results"]), 2)


if __name__ == "__main__":
    unittest.main()
