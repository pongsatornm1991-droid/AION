"""Inspectable campaign queue for human-administered social groups.

Facebook Groups do not expose a safe publishing/reply API in AION.  This
registry therefore models only the work AION can prepare and the observable
status a human can confirm.  It never claims that a submitted group post is
published, approved, monitored, or replied to automatically.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "content" / "group_campaigns" / "registry.json"


class CommunityCampaignRegistry:
    """Read a small, durable queue of distinct group-specific campaigns."""

    VALID_STATUSES = {"ready", "submitted-pending-admin", "approved", "published", "paused"}
    TRANSITIONS = {
        "ready": {"submitted-pending-admin", "paused"},
        "submitted-pending-admin": {"approved", "paused"},
        "approved": {"published", "paused"},
        "published": set(),
        "paused": {"ready"},
    }

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

    def transition(self, campaign_id, status, note=""):
        """Persist one observed status change with a tiny audit trail.

        This method accepts only an operator-observed status.  It never tries
        to infer Meta approval, invent engagement, or perform a network call.
        """
        campaign_id = str(campaign_id or "").strip()
        status = str(status or "").strip()
        if not campaign_id:
            raise ValueError("campaign id is required")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"unknown campaign status: {status}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("campaign registry cannot be read") from exc
        rows = payload.get("campaigns") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("campaign registry has no campaigns list")

        target = next((row for row in rows if isinstance(row, dict) and row.get("id") == campaign_id), None)
        if target is None:
            raise ValueError(f"unknown campaign id: {campaign_id}")
        previous = str(target.get("status") or "ready")
        if previous == status:
            return {"stage": "unchanged", "campaign": dict(target)}
        if status not in self.TRANSITIONS.get(previous, set()):
            raise ValueError(f"invalid campaign transition: {previous} -> {status}")

        observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        target["status"] = status
        target.setdefault("status_history", []).append({
            "from": previous, "to": status, "observed_at": observed_at,
            "note": str(note or "").strip(),
        })
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"stage": "updated", "campaign": dict(target)}

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
