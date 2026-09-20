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
    # Shorts are the current primary format. Thursday through Sunday gives a
    # four-release cadence while Monday–Wednesday remain the production buffer.
    SHORT_DAYS = {3, 4, 5, 6}  # Thursday, Friday, Saturday, Sunday
    # A complete Thu–Sun release set must be visible even when the check runs
    # on Monday morning. A seven-day horizon reaches Sunday evening and avoids
    # falsely calling a four-Short buffer healthy.
    HORIZON_HOURS = 168

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
                slot = datetime(day.year, day.month, day.day, 20, 30, tzinfo=cls.BANGKOK)
                kind = "short"
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
        available = {"short": []}
        for item in candidates:
            is_ready = item.get("status") in {"upload-ready", "already-prepared"}
            is_authorized = item.get("publication_status") == "authorized-for-aion-publish"
            # A rendered file or a historical authorization is not proof that
            # the finished video is safe to schedule.  Readiness is used to
            # protect fixed release slots, so it must require a durable pass
            # from the actual quality gate rather than infer one.
            gate = item.get("quality_gate") or item.get("video_qa") or {}
            quality_passed = gate.get("eligible") is True
            if item.get("release_eligible") and quality_passed and (is_ready or is_authorized):
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
            "shorts_buffer": {
                "target": 4,
                "quality_ready": len(available.get("short", [])),
                "state": "ready" if len(available.get("short", [])) >= 4 else "building",
                "detail": "นับเฉพาะ Shorts ใหม่ที่ผ่าน Quality Gate แล้ว; storyboard หรือภาพครบยังไม่นับเป็นบัฟเฟอร์",
            },
            "policy": "ตรวจล่วงหน้า 144 ชั่วโมง; นับเฉพาะตอนใหม่ที่ผ่าน Quality Gate พร้อมและไม่ซ้ำ ไม่ใช้คลิปเก่าแทนวันปล่อย",
        }
