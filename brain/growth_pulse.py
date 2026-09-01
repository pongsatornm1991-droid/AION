"""A compact daily view of AION's public activity and inner growth."""

import json
from datetime import datetime


class GrowthPulse:
    """Persist one idempotent, human-readable daily growth snapshot."""

    CATEGORY = "growth_pulse"
    SOURCE_PREFIX = "aion-daily-pulse:"

    def __init__(self, memory, now=None):
        self.memory = memory
        self.now = now or datetime.now

    def _latest_instagram(self):
        latest = None
        for entry in self.memory.all("social_feedback"):
            if entry.get("source") != "instagram-feedback":
                continue
            try:
                payload = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if payload.get("kind") == "account":
                latest = payload
        return latest

    def _channel_activity(self):
        counts = {"instagram_reels": 0, "facebook_reels": 0, "youtube_shorts": 0}
        for entry in self.memory.all("published_reels"):
            try:
                payload = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            actions = payload.get("platform_actions") or payload.get("action") or {}
            counts["instagram_reels"] += bool(actions.get("instagram"))
            counts["facebook_reels"] += bool(actions.get("facebook"))
            counts["youtube_shorts"] += bool((payload.get("youtube") or {}).get("video_id"))
        return counts

    def _new_count(self, category):
        today = self.now().strftime("%Y-%m-%d")
        return sum(
            1 for entry in self.memory.all(category)
            if str(entry.get("timestamp", "")).startswith(today)
        )

    def capture_once(self):
        date_key = self.now().strftime("%Y-%m-%d")
        source = f"{self.SOURCE_PREFIX}{date_key}"
        if any(entry.get("source") == source for entry in self.memory.all(self.CATEGORY)):
            return {"stage": "already-reported", "date": date_key}

        report = {
            "stage": "captured",
            "date": date_key,
            "instagram": self._latest_instagram(),
            "activity": self._channel_activity(),
            "learning": {
                "lessons": self._new_count("lessons"),
                "questions": self._new_count("questions"),
                "goals": self._new_count("goals"),
                "reflections": self._new_count("reflections"),
            },
        }
        self.memory.remember(
            category=self.CATEGORY,
            content=json.dumps(report, ensure_ascii=False, sort_keys=True),
            memory_type="observation",
            source=source,
            importance=2,
            tags=["growth", "daily-pulse", "social"],
        )
        return report
