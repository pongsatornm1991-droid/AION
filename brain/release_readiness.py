"""Early warning for AION's fixed Creator release appointments.

This is deliberately an observer, not another publisher.  It answers one
operational question early enough to recover: do the next scheduled release
slots have distinct, quality-eligible Studio episodes waiting already?
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from brain.youtube_creator_queue import YouTubeCreatorQueue


class ReleaseReadiness:
    """Keep the fixed Bangkok publishing cadence from failing silently."""

    BANGKOK = ZoneInfo("Asia/Bangkok")
    SHORT_DAYS = {0, 2, 4, 5}  # Monday, Wednesday, Friday, Saturday
    HORIZON_HOURS = 96

    def __init__(self, memory, root=None):
        self.memory = memory
        self.root = root

    @classmethod
    def slots(cls, now=None, horizon_hours=None):
        now = (now or datetime.now(cls.BANGKOK)).astimezone(cls.BANGKOK)
        horizon = now + timedelta(hours=horizon_hours or cls.HORIZON_HOURS)
        values = []
        for offset in range(0, 8):
            day = (now + timedelta(days=offset)).date()
            weekday = day.weekday()
            if weekday in cls.SHORT_DAYS:
                slot = datetime(day.year, day.month, day.day, 20, 43, tzinfo=cls.BANGKOK)
                kind = "short"
            elif weekday == 6:
                slot = datetime(day.year, day.month, day.day, 20, 15, tzinfo=cls.BANGKOK)
                kind = "long-form"
            else:
                continue
            if now < slot <= horizon:
                values.append({"at": slot.isoformat(), "content_kind": kind})
        return values

    def snapshot(self, now=None):
        slots = self.slots(now)
        try:
            candidates = YouTubeCreatorQueue(self.memory, root=self.root).candidates()
        except (OSError, ValueError, TypeError):
            candidates = []
        available = {"short": [], "long-form": []}
        for item in candidates:
            is_ready = item.get("status") in {"upload-ready", "already-prepared"}
            is_authorized = item.get("publication_status") == "authorized-for-aion-publish"
            if item.get("release_eligible") and (is_ready or is_authorized):
                available.setdefault(item.get("content_kind"), []).append(item.get("episode_id"))
        required = {kind: sum(slot["content_kind"] == kind for slot in slots) for kind in available}
        shortages = []
        for kind, count in required.items():
            have = len(available.get(kind, []))
            if have < count:
                shortages.append({"content_kind": kind, "needed": count, "ready": have, "missing": count - have})
        return {
            "generated_at": (now or datetime.now(self.BANGKOK)).astimezone(self.BANGKOK).isoformat(),
            "timezone": "Asia/Bangkok",
            "horizon_hours": self.HORIZON_HOURS,
            "state": "ready" if not shortages else "attention",
            "slots": slots,
            "available": available,
            "shortages": shortages,
            "policy": "ตรวจล่วงหน้า 96 ชั่วโมง; นับเฉพาะตอนใหม่ที่พร้อมและไม่ซ้ำ ไม่ใช้คลิปเก่าแทนวันปล่อย",
        }
