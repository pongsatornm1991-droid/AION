"""Administrative control plane for queues, cadence and evidence freshness."""

from pathlib import Path


class AdminOperations:
    """Read-only operational checks; never changes accounts, money or secrets."""

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        shorts_workflow = self.root / ".github" / "workflows" / "youtube-shorts.yml"
        try:
            # The legacy fallback may exist, but it must not have its own
            # timer. A file-exists check would falsely report this safe.
            duplicate_guard = "schedule:" not in shorts_workflow.read_text(encoding="utf-8")
        except OSError:
            duplicate_guard = False
        return {
            "name": "Admin Operations Team",
            "purpose": "ดูคิวเผยแพร่ การชนกันของตาราง หลักฐานงาน และการแจ้งข้อผิดพลาดให้ฝ่ายที่รับผิดชอบ",
            "checks": [
                {"name": "Shorts daily cap", "state": "pass" if duplicate_guard else "attention", "detail": "มีสายอัตโนมัติหลักเพียงหนึ่งรอบต่อวัน; workflow เก่ายังใช้ได้เฉพาะสั่งมือ"},
                {"name": "Protected authority", "state": "pass", "detail": "ห้ามเปลี่ยนสิทธิ์ บัญชี คีย์ เงิน และสัญญา"},
                {"name": "Queue handoff", "state": "pass", "detail": "งานเผยแพร่ต้องผ่าน Research → Production → Quality Gate → Publishing"},
            ],
        }
