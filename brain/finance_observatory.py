"""Read-only accounting snapshot for AION operations.

It measures completed work from durable project files.  It never creates a
provider credential, purchases credit, changes a budget, or exposes a secret.
Reconciled OpenAI cost data is optional and requires an owner-provisioned,
read-only Admin API key; Gemini balance remains an owner-console value because
the public Gemini API does not provide a general balance endpoint.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


class FinanceObservatory:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    @staticmethod
    def _openai_costs():
        """Read reconciled month-to-date costs without ever returning a key."""
        enabled = os.getenv("AION_FINANCE_OPENAI_COSTS_ENABLED", "").lower() == "true"
        admin_key = os.getenv("OPENAI_ADMIN_KEY")
        if not (enabled and admin_key):
            return None, "owner-setup-required"
        now = datetime.now(timezone.utc)
        start_time = int(datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp())
        request = Request(
            "https://api.openai.com/v1/organization/costs"
            f"?start_time={start_time}&bucket_width=1d&limit=31",
            headers={"Authorization": f"Bearer {admin_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            value = sum(
                float(result.get("amount", {}).get("value") or 0)
                for bucket in payload.get("data") or []
                for result in bucket.get("results") or []
            )
            return f"${value:,.4f} USD", "synced"
        except (URLError, OSError, ValueError, TypeError):
            # A billing read error must remain visible but may never reveal
            # provider responses or credentials on the dashboard.
            return None, "sync-unavailable"

    def snapshot(self):
        scene_root = self.root / "assets" / "content-library" / "aion-stories"
        scene_images = list(scene_root.rglob("*.png")) if scene_root.is_dir() else []
        videos = list((self.root / "content" / "reels").glob("*.mp4"))
        openai_cost, openai_state = self._openai_costs()
        return {
            "title": "ห้องบัญชี AION",
            "purpose": "ศูนย์บันทึกงานผลิตและต้นทุนที่ยืนยันได้ เพื่อให้ประธานตรวจสอบการใช้ทรัพยากรของ AION โดยไม่ให้ระบบแตะเงินหรือข้อมูลรับรอง",
            "operations": {
                "generated_scene_images": len(scene_images),
                "assembled_videos": len(videos),
                "known_currency_cost": openai_cost,
                "currency_status": "ต้นทุนสะสมตั้งแต่ต้นเดือนจาก OpenAI Costs API" if openai_state == "synced" else "ยังไม่มีการเชื่อมข้อมูลต้นทุนที่ยืนยันได้",
            },
            "providers": [
                {
                    "name": "OpenAI",
                    "state": openai_state,
                    "detail": "ดึงต้นทุนจริงรายวัน/โปรเจกต์ได้ผ่าน Costs API เมื่อประธานใส่ Admin API key แบบอ่านอย่างเดียวและเปิดการซิงก์",
                    "remaining": "ต้นทุนเดือนล่าสุดที่ยืนยันแล้ว" if openai_cost else "ไม่มีข้อมูลยอดคงเหลือในระบบตอนนี้",
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
