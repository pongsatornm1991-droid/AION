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
    # Shorts are the current primary format, published every day since
    # 2026-09-21 (previously Thursday-Sunday only, with Monday-Wednesday
    # reserved as a production-only buffer window). Kept as an explicit set
    # rather than "every day" in code so a future format change (e.g.
    # carving a day back out for research) is a one-line edit here.
    SHORT_DAYS = {0, 1, 2, 3, 4, 5, 6}  # every day
    # A complete week of release slots must be visible even when the check
    # runs first thing in the morning. A seven-day horizon reaches a full
    # week out and avoids falsely calling a seven-Short buffer healthy.
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
            if item.get("status") == "published":
                # `publication_status` below is the durable `upload_status`
                # field, which stays "authorized-for-aion-publish" even after
                # the episode is actually released -- publishing adds a
                # youtube.video_id, it does not change upload_status. Without
                # this check, an already-published episode kept counting as
                # "available" (found 2026-09-22: Venus flytrap, published
                # 2026-09-21, still showed up here a full day later), making
                # the Shorts buffer look one episode healthier than reality.
                continue
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
                "target": len(self.SHORT_DAYS),
                "quality_ready": len(available.get("short", [])),
                "state": "ready" if len(available.get("short", [])) >= len(self.SHORT_DAYS) else "building",
                "detail": "นับเฉพาะ Shorts ใหม่ที่ผ่าน Quality Gate แล้ว; storyboard หรือภาพครบยังไม่นับเป็นบัฟเฟอร์",
            },
            "policy": "ตรวจล่วงหน้า 144 ชั่วโมง; นับเฉพาะตอนใหม่ที่ผ่าน Quality Gate พร้อมและไม่ซ้ำ ไม่ใช้คลิปเก่าแทนวันปล่อย",
        }
