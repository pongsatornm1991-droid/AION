"""Deterministic, bounded repairs for known AION operational faults.

This is intentionally not an arbitrary code-writing agent.  It may repair
only reversible production artifacts whose source is already approved in the
repository, then records exactly what it did.  Source code, credentials,
permissions, spending, policy, and public-account settings are out of scope.
"""

from pathlib import Path

from brain.asset_hygiene import AssetHygiene
from tools.assemble_creator_episode import backfill_subtitles_once


class SafeRepairAgent:
    """Repair known recoverable artifacts once, without publishing anything."""

    def __init__(self, root=None, memory_root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.memory_root = Path(memory_root) if memory_root else self.root / "memory"

    def run_once(self):
        created = []
        for relative in ("content/images", "content/reels", "content/quarantine"):
            directory = self.root / relative
            if not directory.is_dir():
                directory.mkdir(parents=True, exist_ok=True)
                created.append(relative)

        try:
            subtitles = backfill_subtitles_once(self.root)
        except (OSError, ValueError, TypeError) as exc:
            subtitles = {"stage": "subtitle-backfill-failed", "count": 0, "error": str(exc)}
        hygiene = AssetHygiene(self.root, self.memory_root).scan()["summary"]
        repaired = len(created) + int(subtitles.get("count") or 0)
        return {
            "stage": "repaired" if repaired else "checked-no-repair-needed",
            "repaired_count": repaired,
            "created_directories": created,
            "subtitle_backfill": subtitles,
            "asset_hygiene": hygiene,
            "boundary": "ซ่อมได้เฉพาะโฟลเดอร์งานและ caption track ที่สร้างใหม่จาก storyboard เดิม; ไม่แก้โค้ด สิทธิ์ ข้อมูลรับรอง เงิน กฎความปลอดภัย หรือเผยแพร่งาน",
            "next": "ข้อผิดพลาดนอกบัญชีซ่อมที่กำหนดจะถูกแสดงใน Operations Center พร้อมหลักฐาน เพื่อให้เกิดการแก้โค้ดที่ทดสอบได้ ไม่ใช่การแก้แบบเดาสุ่ม",
        }
