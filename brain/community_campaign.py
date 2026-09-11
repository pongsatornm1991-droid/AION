"""Inspectable campaign queue for human-administered social groups.

Facebook Groups do not expose a safe publishing/reply API in AION.  This
registry therefore models only the work AION can prepare and the observable
status a human can confirm.  It never claims that a submitted group post is
published, approved, monitored, or replied to automatically.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "content" / "group_campaigns" / "registry.json"


class CommunityCampaignRegistry:
    """Read a small, durable queue of distinct group-specific campaigns."""

    VALID_STATUSES = {"ready", "submitted-pending-admin", "approved", "published", "paused"}

    def __init__(self, path=None):
        self.path = Path(path or DEFAULT_REGISTRY)

    def campaigns(self):
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        values = payload.get("campaigns") if isinstance(payload, dict) else None
        if not isinstance(values, list):
            return []

        seen = set()
        result = []
        for raw in values:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            key = str(item.get("id") or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            status = str(item.get("status") or "ready")
            item["status"] = status if status in self.VALID_STATUSES else "paused"
            item["id"] = key
            result.append(item)
        return result

    def snapshot(self):
        campaigns = self.campaigns()
        waiting = [item for item in campaigns if item["status"] == "submitted-pending-admin"]
        ready = [item for item in campaigns if item["status"] == "ready"]
        current = waiting[0] if waiting else None
        return {
            "current": current,
            "ready_count": len(ready),
            "waiting_admin_count": len(waiting),
            "campaigns": campaigns,
            "next": (
                "รอผู้ดูแลกลุ่มอนุมัติโพสต์ที่ส่งแล้วก่อน แล้วจึงเลือกเผยแพร่เพียงหนึ่งโพสต์ถัดไป"
                if waiting else
                "มีโพสต์เฉพาะกลุ่มพร้อมเตรียมเผยแพร่ แต่ต้องตรวจสถานะกลุ่มและยืนยันก่อนเผยแพร่"
            ),
            "boundary": "AION เตรียมงานและติดตามสถานะที่ยืนยันได้ แต่ยังไม่ตอบคอมเมนต์หรือโพสต์ใน Facebook Groups อัตโนมัติ.",
        }
