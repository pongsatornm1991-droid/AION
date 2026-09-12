"""Read-only defensive cyber and reliability checks for AION Company."""

from pathlib import Path

from brain.system_reliability import SystemReliability


class CyberGuard:
    """Detect configuration and release hygiene gaps; never attack or alter systems."""

    REQUIRED_GITIGNORE = (".env", "config.env", "client_secret.json")

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        ignored = ""
        try:
            ignored = (self.root / ".gitignore").read_text(encoding="utf-8")
        except OSError:
            pass
        missing = [item for item in self.REQUIRED_GITIGNORE if item not in ignored]
        reliability = SystemReliability(self.root).snapshot()
        checks = [
            {"name": "การปกป้องข้อมูลรับรอง", "state": "pass" if not missing else "attention",
             "detail": "ไฟล์ข้อมูลรับรองหลักถูกกันออกจาก Git" if not missing else f"ต้องเพิ่มใน .gitignore: {', '.join(missing)}"},
            {"name": "ไฟล์แกนกลาง", "state": "pass" if reliability["status"] == "healthy" else "attention",
             "detail": reliability["scope"] if reliability["status"] == "healthy" else f"ไฟล์ขาด: {', '.join(reliability['missing'])}"},
            {"name": "ขอบเขตการตรวจ", "state": "pass",
             "detail": "Cyber Guard ตรวจเชิงป้องกันและรายงานเท่านั้น ไม่สแกนโจมตี ไม่เข้าบัญชี และไม่แตะ secrets"},
        ]
        return {"status": "healthy" if all(item["state"] == "pass" for item in checks) else "needs-attention", "checks": checks}
