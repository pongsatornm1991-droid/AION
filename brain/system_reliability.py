"""Safe, read-only health checks owned by AION's engineering team.

This is intentionally an inspection tool, not an autonomous code editor.  It
turns failures into evidence for the Dev and QA Agents, while account access,
secrets, spending, and security-boundary changes remain protected actions.
"""

from pathlib import Path


class SystemReliability:
    """Inspect the minimum foundations needed for a safe release decision."""

    REQUIRED_PATHS = (
        "main.py",
        "run_tests.py",
        "brain/autonomy_policy.py",
        "tools/dashboard.py",
        ".github/workflows/tests.yml",
        ".github/workflows/system-reliability.yml",
    )

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        missing = [path for path in self.REQUIRED_PATHS if not (self.root / path).is_file()]
        return {
            "status": "healthy" if not missing else "needs-attention",
            "missing": missing,
            "scope": "ตรวจไฟล์แกนกลางและ workflow ทดสอบแบบอ่านอย่างเดียว",
            "boundary": "การตรวจนี้ไม่แก้โค้ด ไม่แตะ secrets สิทธิ์บัญชี การเงิน หรือข้อมูลภายนอก",
        }
