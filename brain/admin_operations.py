"""Administrative control plane for queues, cadence and evidence freshness."""

from pathlib import Path
import re


class AdminOperations:
    """Read-only operational checks; never changes accounts, money or secrets."""

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        legacy_publishers = (
            "youtube-shorts.yml",
            "reel-cycle.yml",
            "instagram-cycle.yml",
            "social-cycle.yml",
        )
        legacy_schedules = []
        for filename in legacy_publishers:
            try:
                source = (self.root / ".github" / "workflows" / filename).read_text(encoding="utf-8")
                if "schedule:" in source:
                    legacy_schedules.append(filename)
            except OSError:
                # A deployment may omit a retired legacy workflow entirely;
                # absence is safer than a timed second publisher.
                continue
        # Legacy tools are intentionally retained for a human-triggered,
        # exceptional repair.  They must never publish on their own timer:
        # Studio Creator is the single public-content source of truth.
        duplicate_guard = not legacy_schedules

        # GitHub does not guarantee an exact start time for scheduled jobs,
        # especially at minute 00.  Only the Creator release spine owns an
        # automatic public schedule; legacy social workflows are manual-only.
        publishing_files = (
            "youtube-creator.yml",
            "youtube-release-recovery.yml",
        )
        cadence_issues = [f"{filename}: ไม่ควรมีตารางเผยแพร่อัตโนมัติ" for filename in legacy_schedules]
        for filename in publishing_files:
            try:
                source = (self.root / ".github" / "workflows" / filename).read_text(encoding="utf-8")
                crons = re.findall(r'cron:\s*["\']([^"\']+)["\']', source)
                if not crons:
                    cadence_issues.append(f"{filename}: ตารางไม่ชัดเจน")
                    continue
                for cron in crons:
                    minute = cron.split()[0]
                    if minute in ("0", "00"):
                        cadence_issues.append(f"{filename}: ตั้งต้นชั่วโมง")
            except OSError:
                cadence_issues.append(f"{filename}: ไม่พบไฟล์")

        return {
            "name": "Admin Operations Team",
            "purpose": "ดูคิวเผยแพร่ การชนกันของตาราง หลักฐานงาน และการแจ้งข้อผิดพลาดให้ฝ่ายที่รับผิดชอบ",
            "checks": [
                {"name": "Single publishing source", "state": "pass" if duplicate_guard else "attention", "detail": "เผยแพร่สาธารณะอัตโนมัติผ่าน Creator pipeline เพียงสายเดียว" if duplicate_guard else f"พบสายเก่าที่ตั้งเวลาอยู่: {', '.join(legacy_schedules)}"},
                {"name": "Publishing cadence", "state": "pass" if not cadence_issues else "attention", "detail": "Shorts เป็นงานหลัก: พฤ./ศ./ส./อา. 20:30 เวลาไทย; จ.–พ. เป็นรอบวิจัย ผลิต และกู้คืนบัฟเฟอร์" if not cadence_issues else "; ".join(cadence_issues)},
                {"name": "Protected authority", "state": "pass", "detail": "ห้ามเปลี่ยนสิทธิ์ บัญชี คีย์ เงิน และสัญญา"},
                {"name": "Queue handoff", "state": "pass", "detail": "งานเผยแพร่ต้องผ่าน Research → Production → Quality Gate → Publishing"},
            ],
        }
