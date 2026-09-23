"""Compare one published episode's real audience engagement against others.

Exists because AION's own curiosity engine raised exactly this question
(root_question_id b89b0b48c59c, 2026-09-22: "is this video's like-to-view
ratio higher or lower than similar videos on the same channel?") and had
no way to answer it -- WebLearningCycle wastefully searched Wikipedia
three times, each attempt correctly finding nothing relevant, since
Wikipedia cannot know AION's own YouTube statistics (see
EvidenceRequirementAnalyzer.PLATFORM_METRICS_TERMS in brain/learning.py
for the fix that stops the wasted attempts).

The data needed already exists: YouTubeAudienceCycle
(brain/youtube_audience.py) writes public view/like/comment-count
snapshots to the same `social_feedback` memory category
InstagramFeedbackCycle and the Growth Engine already read -- it just had
no comparison analysis on top of it. This module is that analysis: small,
standalone, and deterministic (no AI provider call, no network access of
its own).

The underlying snapshots are also exposed to the autonomous learning loop
through the enabled ``social_signals`` adapter. This comparison stays a
separate deterministic tool because it supplies a stricter median-based
answer than a general evidence-summary draft. It is available directly as
``python main.py compare-video-engagement`` for an audited answer with real
numbers rather than a guess.
"""

import json


class PerformanceFeedback:
    """Deterministic engagement comparisons over AION's own captured stats."""

    CATEGORY = "social_feedback"
    SOURCE = "youtube-public-analytics"

    def __init__(self, memory):
        self.memory = memory

    def _latest_youtube_snapshots(self):
        """One snapshot per video_id: the most recently recorded.

        YouTubeAudienceCycle only ever writes a new entry when a value
        actually changed, so the entry with the latest timestamp per
        video_id is always its most current known statistics.
        """
        latest = {}
        for entry in self.memory.all(self.CATEGORY):
            if entry.get("source") != self.SOURCE:
                continue
            try:
                payload = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if not isinstance(payload, dict) or not payload.get("video_id"):
                continue
            video_id = payload["video_id"]
            timestamp = str(entry.get("timestamp") or "")
            if video_id not in latest or timestamp >= latest[video_id][0]:
                latest[video_id] = (timestamp, payload)
        return {video_id: payload for video_id, (_, payload) in latest.items()}

    @staticmethod
    def _like_to_view_ratio(snapshot):
        views = int(snapshot.get("view_count") or 0)
        likes = int(snapshot.get("like_count") or 0)
        if views <= 0:
            return None
        return likes / views

    def compare_engagement(self, video_id, min_group_size=3):
        """Compare one video's like-to-view ratio against the median of others.

        Never invents a comparison group: with fewer than `min_group_size`
        OTHER videos carrying usable statistics, this honestly reports
        insufficient data rather than comparing against a handful of
        unrepresentative videos. Only ever reads already-captured public
        statistics; makes no network call and never estimates a number
        that was not actually recorded.
        """
        snapshots = self._latest_youtube_snapshots()
        target = snapshots.get(video_id)
        if target is None:
            return {"stage": "no-statistics-for-video", "video_id": video_id}
        target_ratio = self._like_to_view_ratio(target)
        if target_ratio is None:
            return {"stage": "video-has-no-views-yet", "video_id": video_id}

        others = [
            ratio for other_id, snapshot in snapshots.items()
            if other_id != video_id
            for ratio in [self._like_to_view_ratio(snapshot)]
            if ratio is not None
        ]

        if len(others) < min_group_size:
            return {
                "stage": "insufficient-comparison-data",
                "video_id": video_id,
                "target_ratio": round(target_ratio, 4),
                "comparison_group_size": len(others),
                "required_group_size": min_group_size,
            }

        others_sorted = sorted(others)
        mid = len(others_sorted) // 2
        median_ratio = (
            others_sorted[mid] if len(others_sorted) % 2
            else (others_sorted[mid - 1] + others_sorted[mid]) / 2
        )
        difference_pct = ((target_ratio - median_ratio) / median_ratio * 100) if median_ratio else None
        if difference_pct is None:
            verdict = "unknown"
        elif difference_pct > 5:
            verdict = "higher"
        elif difference_pct < -5:
            verdict = "lower"
        else:
            verdict = "similar"
        return {
            "stage": "compared",
            "video_id": video_id,
            "target_ratio": round(target_ratio, 4),
            "comparison_group_size": len(others),
            "median_ratio": round(median_ratio, 4),
            "difference_pct": round(difference_pct, 1) if difference_pct is not None else None,
            "verdict": verdict,
        }
