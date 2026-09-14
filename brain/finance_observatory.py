"""Read-only accounting snapshot for AION operations.

It measures completed work from durable project files.  It never creates a
provider credential, purchases credit, changes a budget, or exposes a secret.
Reconciled OpenAI cost data is optional and requires an owner-provisioned,
read-only Admin API key; Gemini balance remains an owner-console value because
the public Gemini API does not provide a general balance endpoint.
"""

import os
from pathlib import Path


class FinanceObservatory:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        scene_root = self.root / "assets" / "content-library" / "aion-stories"
        scene_images = list(scene_root.rglob("*.png")) if scene_root.is_dir() else []
        videos = list((self.root / "content" / "reels").glob("*.mp4"))
        openai_costs_enabled = os.getenv("AION_FINANCE_OPENAI_COSTS_ENABLED", "").lower() == "true"
        openai_admin_available = bool(os.getenv("OPENAI_ADMIN_KEY"))
        return {
            "title": "AION Finance Observatory",
            "purpose": "ติดตามหน่วยงานผลิตและต้นทุนที่ผู้ให้บริการยืนยัน โดยอ่านอย่างเดียว",
            "operations": {
                "generated_scene_images": len(scene_images),
                "assembled_videos": len(videos),
                "known_currency_cost": None,
                "currency_status": "รอข้อมูลค่าใช้จ่ายที่ยืนยันจากผู้ให้บริการ",
            },
            "providers": [
                {
                    "name": "OpenAI",
                    "state": "ready-for-readonly-cost-sync" if (openai_costs_enabled and openai_admin_available) else "owner-setup-required",
                    "detail": "ดึงต้นทุนจริงรายวัน/โปรเจกต์ได้ผ่าน Costs API เมื่อประธานใส่ Admin API key แบบอ่านอย่างเดียวและเปิดการซิงก์",
                    "remaining": "ไม่มีข้อมูลยอดคงเหลือในระบบตอนนี้",
                },
                {
                    "name": "Gemini",
                    "state": "owner-console-required",
                    "detail": "ยอดใช้และเครดิตดูได้ใน Google AI Studio/Cloud Billing; ระบบจะไม่เดาหรืออ่านเงินผ่าน API key ปกติ",
                    "remaining": "เปิดดูจาก AI Studio Billing หรือ Cloud Billing",
                },
            ],
            "boundary": "ห้องนี้อ่านและสรุปเท่านั้น AION ไม่มีสิทธิ์ซื้อเครดิต เติมเงิน ตั้ง auto-reload เปลี่ยน spend cap หรือเข้าถึงข้อมูลรับรอง",
        }
