"""Bounded research adapter over AION's already-captured public signals.

This is deliberately an internal evidence adapter, not a social-network
scraper.  Platform cycles are responsible for authenticated retrieval and
write immutable observations into ``social_feedback``.  The learning loop can
then use only those observations that were actually captured, with a stable
public URL where one is available.

It keeps an important epistemic boundary: counts are audience signals, not
evidence about scientific or historical facts, and aggregate counts are not
individual human perspectives.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


class SocialSignalsSource:
    """Expose latest captured YouTube and Instagram metrics as research items."""

    CATEGORY = "social_feedback"
    SUPPORTED_SOURCES = {
        "youtube-public-analytics",
        "instagram-feedback",
    }

    def __init__(self, memory):
        self.memory = memory
        self._results: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _key(source, payload):
        if source == "youtube-public-analytics" and payload.get("video_id"):
            return f"youtube:{payload['video_id']}"
        if source == "instagram-feedback" and payload.get("kind") == "media" and payload.get("media_id"):
            return f"instagram-media:{payload['media_id']}"
        if source == "instagram-feedback" and payload.get("kind") == "account":
            return "instagram-account"
        return None

    def _latest(self):
        latest = {}
        for entry in self.memory.all(self.CATEGORY):
            source = str(entry.get("source") or "").strip()
            if source not in self.SUPPORTED_SOURCES:
                continue
            payload = self._payload(entry)
            if not payload:
                continue
            key = self._key(source, payload)
            if not key:
                continue
            timestamp = str(entry.get("timestamp") or "")
            if key not in latest or timestamp >= latest[key][0]:
                latest[key] = (timestamp, source, payload)
        return latest

    @staticmethod
    def _url(source, payload):
        if source == "youtube-public-analytics":
            video_id = str(payload.get("video_id") or "").strip()
            return f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        permalink = str(payload.get("permalink") or "").strip()
        if permalink.startswith(("https://", "http://")):
            return permalink
        username = str(payload.get("username") or "").strip().lstrip("@")
        return f"https://www.instagram.com/{username}/" if username else ""

    @staticmethod
    def _title(source, payload):
        if source == "youtube-public-analytics":
            return f"AION YouTube public metrics: {payload.get('video_id', '')}".strip()
        if payload.get("kind") == "account":
            return "AION Instagram account public metrics"
        return f"AION Instagram post public metrics: {payload.get('media_id', '')}".strip()

    @staticmethod
    def _extract(source, payload, captured_at):
        if source == "youtube-public-analytics":
            return (
                "AION captured these public YouTube statistics "
                f"at {captured_at or 'an unspecified time'}: video_id={payload.get('video_id')}; "
                f"title={payload.get('title') or 'untitled'}; views={int(payload.get('view_count') or 0)}; "
                f"likes={int(payload.get('like_count') or 0)}; comments={int(payload.get('comment_count') or 0)}. "
                "These are platform counters only; they do not reveal retention, demographics, or why viewers reacted."
            )
        if payload.get("kind") == "account":
            return (
                "AION captured these public Instagram account counters "
                f"at {captured_at or 'an unspecified time'}: username={payload.get('username') or 'unknown'}; "
                f"followers={int(payload.get('followers_count') or 0)}; media={int(payload.get('media_count') or 0)}. "
                "These aggregate counters are audience signals, not individual opinions."
            )
        return (
            "AION captured these public Instagram post counters "
            f"at {captured_at or 'an unspecified time'}: media_id={payload.get('media_id')}; "
            f"likes={int(payload.get('like_count') or 0)}; comments={int(payload.get('comments_count') or 0)}; "
            f"caption={str(payload.get('caption') or '')[:280]}. "
            "These aggregate counters are audience signals, not individual opinions."
        )

    @staticmethod
    def _matches(query, record):
        words = set(re.findall(r"[a-z0-9_-]{3,}", str(query or "").lower()))
        if not words:
            return True
        haystack = " ".join(str(record.get(key) or "").lower() for key in ("title", "url", "extract"))
        return bool(words & set(re.findall(r"[a-z0-9_-]{3,}", haystack)))

    def search(self, query, limit=10):
        records = []
        for _key, (timestamp, source, payload) in self._latest().items():
            record = {
                "title": self._title(source, payload),
                "url": self._url(source, payload),
                "extract": self._extract(source, payload, timestamp),
                "timestamp": timestamp,
            }
            records.append(record)
        records.sort(key=lambda row: (row["timestamp"], row["title"]), reverse=True)
        matches = [row for row in records if self._matches(query, row)] or records
        self._results = {row["title"]: row for row in matches}
        return [{"title": row["title"], "url": row["url"]} for row in matches[:max(1, int(limit))]]

    def fetch(self, title):
        return self._results.get(str(title or "").strip())

    def adapter(self):
        return {"search": self.search, "fetch": self.fetch}
