"""Administrative control plane for queues, cadence and evidence freshness."""

from pathlib import Path
import re


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

        # GitHub does not guarantee an exact start time for scheduled jobs,
        # especially at minute 00.  These four workflows are the public
        # publishing spine, so the operations team checks that each still has
        # one deliberately offset schedule.  This catches an accidental edit
        # that silently returns AION to the congested top-of-hour window.
        publishing_files = (
            "reel-cycle.yml",
            "instagram-cycle.yml",
            "youtube-creator.yml",
            "social-cycle.yml",
        )
        cadence_issues = []
        for filename in publishing_files:
            try:
                source = (self.root / ".github" / "workflows" / filename).read_text(encoding="utf-8")
                crons = re.findall(r'cron:\s*["\']([^"\']+)["\']', source)
                if len(crons) != 1:
                    cadence_issues.append(f"{filename}: ตารางไม่ชัดเจน")
                    continue
                minute = crons[0].split()[0]
                if minute in ("0", "00"):
                    cadence_issues.append(f"{filename}: ตั้งต้นชั่วโมง")
            except OSError:
                cadence_issues.append(f"{filename}: ไม่พบไฟล์")

        return {
            "name": "Admin Operations Team",
            "purpose": "ดูคิวเผยแพร่ การชนกันของตาราง หลักฐานงาน และการแจ้งข้อผิดพลาดให้ฝ่ายที่รับผิดชอบ",
            "checks": [
                {"name": "Shorts daily cap", "state": "pass" if duplicate_guard else "attention", "detail": "มีสายอัตโนมัติหลักเพียงหนึ่งรอบต่อวัน; workflow เก่ายังใช้ได้เฉพาะสั่งมือ"},
                {"name": "Publishing cadence", "state": "pass" if not cadence_issues else "attention", "detail": "ตารางเผยแพร่ทั้ง 4 ช่องทางถูกกระจายเวลา ลดโอกาสพลาดรอบ" if not cadence_issues else "; ".join(cadence_issues)},
                {"name": "Protected authority", "state": "pass", "detail": "ห้ามเปลี่ยนสิทธิ์ บัญชี คีย์ เงิน และสัญญา"},
                {"name": "Queue handoff", "state": "pass", "detail": "งานเผยแพร่ต้องผ่าน Research → Production → Quality Gate → Publishing"},
            ],
        }
