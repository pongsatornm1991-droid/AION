"""Read-only continuity and recovery-readiness checks for AION Company."""

from pathlib import Path

from brain.asset_hygiene import AssetHygiene
from brain.system_reliability import SystemReliability


class ContinuityGuard:
    """Verify that AION can recover work without silently deleting evidence."""

    def __init__(self, root=None, memory_root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.memory_root = Path(memory_root) if memory_root else self.root / "memory"

    def snapshot(self):
        core = SystemReliability(self.root).snapshot()
        assets = AssetHygiene(self.root, self.memory_root).scan()
        memory_versioned = (self.memory_root / ".git").is_dir()
        code_versioned = (self.root / ".git").is_dir()
        quarantine = self.root / "content" / "quarantine"
        checks = [
            {"name": "โค้ดและ workflow", "state": "pass" if core["status"] == "healthy" else "attention", "detail": core["scope"]},
            {"name": "ประวัติงานและความจำ", "state": "pass" if memory_versioned else "waiting", "detail": "ความจำอยู่ใน Git history ที่กู้คืนได้" if memory_versioned else "เครื่องนี้ยังไม่มีสำเนา memory ที่ sync จากคลังส่วนตัว"},
            {"name": "สื่อและไฟล์กำพร้า", "state": "pass" if not assets["summary"]["review"] else "attention", "detail": f"ไฟล์ใช้งาน {assets['summary']['active']} · ต้องตรวจ {assets['summary']['review']} · ย้ายเข้ากักกันแบบกู้คืนได้"},
            {"name": "จุดกู้คืน", "state": "pass" if code_versioned else "attention", "detail": "โค้ดและสื่อย้อนกลับผ่าน Git ได้; ไฟล์ที่ต้องล้างจะย้ายเข้า quarantine ไม่ลบถาวร" if code_versioned else "ไม่พบ Git history ของโครงการนี้"},
        ]
        return {
            "status": "healthy" if all(item["state"] == "pass" for item in checks) else "attention",
            "checks": checks,
            "recovery": "เมื่อ workflow ล้ม ระบบเก็บคิวเดิมไว้ให้รอบถัดไป; เมื่อไฟล์เก่าไม่ถูกอ้างอิง จะกักกันก่อนเสมอ; การกู้คืนใช้ประวัติ Git ไม่แตะข้อมูลรับรองหรือบัญชี",
        }
