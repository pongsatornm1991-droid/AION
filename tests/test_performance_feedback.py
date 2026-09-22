import json
import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from brain.performance_feedback import PerformanceFeedback


class PerformanceFeedbackTests(unittest.TestCase):
    def _record(self, memory, video_id, views, likes):
        memory.remember(
            PerformanceFeedback.CATEGORY,
            json.dumps({
                "kind": "youtube-public-video", "video_id": video_id,
                "view_count": views, "like_count": likes, "comment_count": 0,
            }, ensure_ascii=False),
            memory_type="observation", source=PerformanceFeedback.SOURCE,
            importance=2, tags=["youtube", "audience", "public-metrics", video_id],
        )

    def test_no_statistics_at_all_is_reported_honestly(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            result = PerformanceFeedback(memory).compare_engagement("missing")
            self.assertEqual("no-statistics-for-video", result["stage"])

    def test_zero_views_is_reported_honestly_not_divided_by_zero(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            self._record(memory, "target", views=0, likes=0)
            result = PerformanceFeedback(memory).compare_engagement("target")
            self.assertEqual("video-has-no-views-yet", result["stage"])

    def test_refuses_to_compare_against_too_small_a_group(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            self._record(memory, "target", views=1000, likes=50)
            self._record(memory, "other-1", views=1000, likes=40)
            result = PerformanceFeedback(memory).compare_engagement("target", min_group_size=3)
            self.assertEqual("insufficient-comparison-data", result["stage"])
            self.assertEqual(1, result["comparison_group_size"])

    def test_compares_against_the_median_of_a_sufficient_group(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            self._record(memory, "target", views=1000, likes=100)  # ratio 0.10
            self._record(memory, "other-1", views=1000, likes=40)   # 0.04
            self._record(memory, "other-2", views=1000, likes=50)   # 0.05
            self._record(memory, "other-3", views=1000, likes=60)   # 0.06
            result = PerformanceFeedback(memory).compare_engagement("target", min_group_size=3)
            self.assertEqual("compared", result["stage"])
            self.assertEqual(3, result["comparison_group_size"])
            self.assertAlmostEqual(0.05, result["median_ratio"])
            self.assertEqual("higher", result["verdict"])

    def test_only_the_latest_snapshot_per_video_counts(self):
        # YouTubeAudienceCycle only writes a new entry when a value
        # changes; an older snapshot for the same video must not also be
        # counted as if it were a distinct comparison video.
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            self._record(memory, "target", views=1000, likes=100)
            self._record(memory, "other-1", views=500, likes=20)
            self._record(memory, "other-1", views=1000, likes=40)  # same video, later snapshot
            self._record(memory, "other-2", views=1000, likes=50)
            self._record(memory, "other-3", views=1000, likes=60)
            result = PerformanceFeedback(memory).compare_engagement("target", min_group_size=3)
            self.assertEqual(3, result["comparison_group_size"])

    def test_similar_verdict_within_5_percent(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            self._record(memory, "target", views=1000, likes=50)   # 0.05
            self._record(memory, "other-1", views=1000, likes=49)
            self._record(memory, "other-2", views=1000, likes=50)
            self._record(memory, "other-3", views=1000, likes=51)
            result = PerformanceFeedback(memory).compare_engagement("target", min_group_size=3)
            self.assertEqual("similar", result["verdict"])


if __name__ == "__main__":
    unittest.main()
