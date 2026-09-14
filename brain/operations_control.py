"""One evidence-backed control tower for AION's autonomous work.

This module deliberately does not publish, alter credentials, spend money, or
rewrite source code.  It joins records already produced by the real company
workflows so the Dashboard can state what is moving, what is waiting, and how
the normal recovery path will handle it.
"""

import json
from pathlib import Path

from brain.asset_hygiene import AssetHygiene
from brain.audience_accessibility import AudienceAccessibility
from brain.company_work_registry import CompanyWorkRegistry
from brain.delivery_watchdog import DeliveryWatchdog
from brain.system_reliability import SystemReliability
from brain.youtube_creator_queue import YouTubeCreatorQueue
from brain.continuity_guard import ContinuityGuard


class OperationsControlTower:
    """Read the company handoffs without creating a second source of truth."""

    PENDING = (
        ("pending_reels", "Reel", "รอรอบเผยแพร่หรือการส่งซ้ำที่ปลอดภัย"),
        ("pending_visual_content", "ภาพ Instagram", "รอรอบเผยแพร่หรือการส่งซ้ำที่ปลอดภัย"),
    )

    def __init__(self, memory, root=None):
        self.memory = memory
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _entries(self, category):
        try:
            return self.memory.all(category)
        except (OSError, ValueError, TypeError):
            return []

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "")
        except (AttributeError, TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _pending_work(self):
        work = []
        for category, label, recovery in self.PENDING:
            entries = self._entries(category)
            if not entries:
                continue
            newest = max(entries, key=lambda item: item.get("timestamp", ""))
            payload = self._payload(newest)
            work.append({
                "lane": "เผยแพร่",
                "name": label,
                "state": "waiting",
                "count": len(entries),
                "detail": payload.get("caption") or recovery,
                "recovery": recovery,
                "timestamp": newest.get("timestamp"),
            })

        try:
            candidates = YouTubeCreatorQueue(self.memory, root=self.root).candidates()
        except (OSError, ValueError, TypeError):
            candidates = []
        for item in candidates:
            status = item.get("publication_status") or item.get("status")
            if status in {"published", "uploaded"}:
                continue
            ready = status in {"authorized-for-aion-publish", "upload-ready"}
            work.append({
                "lane": "YouTube",
                "name": item.get("title") or "ตอน Creator ที่กำลังผลิต",
                "state": "active" if ready else "waiting",
                "count": 1,
                "detail": "ผ่าน Quality Gate พร้อมเข้ารอบเผยแพร่" if ready else "กำลังรอภาพ เสียง การประกอบ หรือ Quality Gate",
                "recovery": "YouTube Creator workflow จะตรวจคิวและเผยแพร่เฉพาะงานที่พร้อมตามรอบของแพลตฟอร์ม",
                "timestamp": item.get("updated_at") or item.get("created_at"),
            })
        return work

    def _creative_gate(self):
        """Expose pass/hold reasons, never an opaque creative score."""
        try:
            from brain.creator_series import CreatorSeriesRegistry
            episodes = CreatorSeriesRegistry(self.root).snapshot()
            return {
                "state": "pass",
                "label": "พร้อมตรวจตาม Quality Gate",
                "detail": f"ตรวจ storyboard {len(episodes)} ตอน: คุณค่าต่อผู้ชม, hook, แหล่งอ้างอิง, ขอบเขตความไม่แน่นอน, จังหวะฉาก และบทบาท AION",
                "episodes": len(episodes),
            }
        except (OSError, ValueError, TypeError) as exc:
            return {
                "state": "attention",
                "label": "ต้องแก้ storyboard ก่อนผลิตต่อ",
                "detail": str(exc),
                "episodes": 0,
            }

    def _preflight(self):
        """Make the existing production gates visible before external upload."""
        try:
            candidates = YouTubeCreatorQueue(self.memory, root=self.root).candidates()
        except (OSError, ValueError, TypeError):
            candidates = []
        items = []
        for item in candidates:
            if item.get("status") == "published":
                continue
            gate = item.get("quality_gate") or {}
            if not item.get("video_exists"):
                state, detail = "waiting", "รอประกอบวิดีโอจากภาพ เสียง และ storyboard"
            elif gate.get("eligible"):
                state, detail = "pass", "ผ่าน Quality Gate แล้ว รอรอบเผยแพร่"
            elif gate.get("state") == "blocked":
                state, detail = "attention", "Quality Gate ระบุสิ่งที่ต้องแก้ไว้แล้ว"
            else:
                state, detail = "waiting", "ก่อนอัปโหลดจะตรวจไฟล์, เสียง, สัดส่วน, ระยะเวลา, frame samples, คุณค่าต่อผู้ชม และงานซ้ำ"
            items.append({"title": item.get("title"), "state": state, "detail": detail, "reasons": gate.get("reasons") or []})
        return items

    def _self_repair(self):
        path = self.root / "public" / "aion-self-repair-status.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"state": "waiting", "label": "รอรอบตรวจซ่อมอัตโนมัติครั้งแรก", "detail": "Self-Repair Agent จะซ่อมเฉพาะรายการที่ขึ้นทะเบียนและตรวจสอบผลก่อนบันทึก"}
        return {
            "state": "pass" if payload.get("stage") in {"repaired", "checked-no-repair-needed"} else "attention",
            "label": "Self-Repair Agent ล่าสุด",
            "detail": f"{payload.get('stage')} · ซ่อม/กู้ได้ {payload.get('repaired_count', 0)} รายการ",
            "report": payload,
        }

    def snapshot(self):
        pending = self._pending_work()
        delivery = DeliveryWatchdog(self.memory, root=self.root).snapshot()
        delivery_attention = [item for item in delivery["platforms"] if item["state"] != "verified"]
        reliability = SystemReliability(self.root).snapshot()
        assets = AssetHygiene(self.root, memory_root=getattr(self.memory, "root", None)).scan()["summary"]
        company = CompanyWorkRegistry(self.root).snapshot()
        workflow_attention = [item for item in company["departments"] if item["state"] in {"failure", "partial", "unknown"}]
        quality = self._creative_gate()
        audience = AudienceAccessibility(self.memory).snapshot()
        continuity = ContinuityGuard(self.root, getattr(self.memory, "root", None)).snapshot()
        self_repair = self._self_repair()

        blockers = []
        for item in pending:
            if item["state"] == "waiting":
                blockers.append({"name": item["name"], "detail": item["recovery"], "state": "waiting"})
        for item in delivery_attention:
            blockers.append({"name": item["platform"].title(), "detail": "ยังไม่มีหลักฐานเผยแพร่ล่าสุด; Delivery Watchdog จะตรวจใหม่โดยไม่โพสต์ซ้ำ", "state": "attention"})
        for item in workflow_attention:
            blockers.append({"name": item["department"], "detail": "ต้องอาศัยผล workflow ล่าสุดก่อนยืนยันว่าการส่งต่องานครบ", "state": "attention"})
        if reliability["status"] != "healthy":
            blockers.append({"name": "โครงสร้างระบบ", "detail": reliability["scope"], "state": "attention"})

        return {
            "title": "AION Operations Control Tower",
            "purpose": "รวมคิวผลิต คุณภาพ การเผยแพร่ ผู้ชม และความน่าเชื่อถือจากหลักฐานจริง เพื่อให้งานไม่ค้างเงียบหรือทำซ้ำ",
            "status": "attention" if blockers or quality["state"] != "pass" else "healthy",
            "work_now": pending,
            "blockers": blockers,
            "quality_gate": quality,
            "preflight": self._preflight(),
            "delivery": delivery,
            "audience": audience,
            "asset_hygiene": assets,
            "continuity": continuity,
            "self_repair": self_repair,
            "workflow_register": company,
            "recovery_policy": "งานที่รอจะถูกเก็บในคิวเดิมและลองใหม่โดย workflow ปกติ; ไม่สร้างโพสต์ซ้ำ ไม่ใช้ภาพเก่าแทน และไม่แตะสิทธิ์บัญชี เงิน หรือข้อมูลรับรอง",
        }
