"""Persist one daily creator-competitive scan into AION's own memory.

tools/creator_competitive_scan.py does the actual YouTube Data API work and
never raises. This module adds the one thing a scheduled job needs on top:
the same "already done today" dedupe CreatorReferenceStudy uses, so a manual
workflow_dispatch re-run on the same day never writes a second, near-
identical record, plus a bounded record size so memory does not grow
unbounded from a source that returns many rows every run.
"""

import json
from datetime import datetime, timezone

from tools.creator_competitive_scan import scan_report

CATEGORY = "creator_competitive_scans"
SOURCE_PREFIX = "aion-competitive-scan:"
TOP_RESULTS_KEPT = 15


class CreatorCompetitiveScanCycle:
    def __init__(self, memory, queries=None, videos_per_query=5, api_key=None, scan_fn=None):
        self.memory = memory
        self.queries = queries
        self.videos_per_query = videos_per_query
        self.api_key = api_key
        self.scan_fn = scan_fn or scan_report

    def _already_scanned(self, source):
        """True only once a *successful* scan exists for this source.

        A failed attempt is still persisted below (for the audit trail),
        but must never count as "already done today" -- otherwise a
        transient failure (a briefly misconfigured API key, a quota hiccup)
        would block every retry, including a manual workflow_dispatch
        re-run meant specifically to try again, for the rest of the day.
        """
        for entry in self.memory.all(CATEGORY):
            if entry.get("source") != source:
                continue
            try:
                if json.loads(entry.get("content") or "{}").get("ok"):
                    return True
            except (TypeError, ValueError):
                continue
        return False

    def scan_once(self, now=None):
        now = now or datetime.now(timezone.utc)
        today = now.date().isoformat()
        source = f"{SOURCE_PREFIX}{today}"
        if self._already_scanned(source):
            return {"stage": "already-scanned-today", "date": today, "saved": False}

        report = self.scan_fn(queries=self.queries, videos_per_query=self.videos_per_query, api_key=self.api_key)
        record = {**report, "results": (report.get("results") or [])[:TOP_RESULTS_KEPT]}
        saved = self.memory.remember(
            CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True),
            memory_type="observation", source=source, importance=2,
            tags=["creator", "competitive-scan", "content-strategy"],
        )
        return {
            "stage": "scanned" if report.get("ok") else "scan-failed",
            "date": today, "saved": bool(saved.get("saved")), "report": record,
        }
