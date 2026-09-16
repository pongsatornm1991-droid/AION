"""Company-wide guard against repeating public AION content.

The publishing queues are not independent creative silos.  This small ledger
looks across social, Studio and YouTube records before a new idea becomes a
brief or a post.  It stores no external data and makes a conservative decision
that is easy to audit.
"""

import json

from brain.topic_novelty import TopicNoveltyGate


class ContentNoveltyLedger:
    """Read the durable content records and reject a repeated subject."""

    CATEGORIES = ("published_reels", "pending_reels", "youtube_creator_queue")

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def records(self):
        records = []
        for category in self.CATEGORIES:
            for entry in self.memory.all(category):
                payload = self._payload(entry)
                if payload:
                    records.append({**payload, "_category": category, "_memory_id": entry.get("id")})
        return records

    def assess(self, candidate, exclude_memory_ids=()):
        candidate = dict(candidate or {})
        excluded = {str(item) for item in exclude_memory_ids if item}
        matches = [
            {"category": item["_category"], "memory_id": item.get("_memory_id"),
             "title": item.get("title") or item.get("caption") or item.get("topic_key")}
            for item in self.records()
            if str(item.get("_memory_id") or "") not in excluded
            if TopicNoveltyGate.same_topic(candidate, item)
        ]
        return {
            "eligible": not matches,
            "reason": None if not matches else "duplicate-topic-company-wide",
            "matches": matches,
        }

    def snapshot(self):
        records = self.records()
        return {
            "tracked_records": len(records),
            "by_queue": {category: sum(item["_category"] == category for item in records)
                         for category in self.CATEGORIES},
            "rule": "หัวข้อหรือแหล่งอ้างอิงที่ซ้ำกับงานคิว/เผยแพร่แล้ว จะไม่ผ่านเข้าการผลิตใหม่",
        }
