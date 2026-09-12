"""Read-only quality checks for the real AION Company operating model.

The audit deliberately reports limitations instead of claiming that a system
is vulnerability-free.  It checks only inspectable project facts and never
changes permissions, secrets, external accounts, or published work.
"""

from brain.autonomy_policy import AutonomyPolicy
from brain.company_operations import CompanyOperations
from brain.company_work_registry import CompanyWorkRegistry


class CompanyQualityAudit:
    """Create a concise, dashboard-safe company health report."""

    def __init__(self, root=None):
        self.root = root

    def snapshot(self):
        operations = CompanyOperations(self.root).audit()
        registry = CompanyWorkRegistry(self.root).snapshot()
        policy = AutonomyPolicy(self.root)
        checks = []

        blocked = [item["id"] for item in operations["departments"] if item["status"] != "operational"]
        checks.append({
            "id": "structure", "title": "โครงสร้างทีมและทางส่งต่องาน",
            "state": "pass" if not blocked else "attention",
            "detail": "ทุกฝ่ายผูกกับโมดูลและ workflow จริง" if not blocked else f"ฝ่ายที่ยังขาดไฟล์: {', '.join(blocked)}",
        })

        protected = policy.data.get("chair_approval_required") or []
        required_terms = ("เงิน", "สิทธิ์", "ข้อมูลรับรอง")
        boundary_ok = policy.public_publishing_enabled and all(any(term in str(item) for item in protected) for term in required_terms)
        checks.append({
            "id": "authority", "title": "อำนาจเผยแพร่และขอบเขตประธาน",
            "state": "pass" if boundary_ok else "attention",
            "detail": "AION เผยแพร่สาธารณะหลัง Quality Gate; เงิน สิทธิ์บัญชี และข้อมูลรับรองยังต้องอนุมัติ" if boundary_ok else "ตรวจนโยบายอำนาจ: ต้องคงข้อจำกัดเรื่องเงิน สิทธิ์บัญชี และข้อมูลรับรอง",
        })

        departments = registry.get("departments") or []
        failures = [item["department"] for item in departments if item["state"] == "failure"]
        unknown = [item["department"] for item in departments if item["state"] in {"unknown", "partial"}]
        checks.append({
            "id": "workflow_health", "title": "หลักฐานการทำงานล่าสุด",
            "state": "attention" if failures or unknown else "pass",
            "detail": (f"ต้องตรวจ workflow ของ: {', '.join(failures + unknown)}" if failures or unknown
                       else "ทุกฝ่ายมีผล workflow ยืนยันล่าสุด"),
        })

        healthy = all(item["state"] == "pass" for item in checks)
        return {
            "status": "healthy" if healthy else "needs-attention",
            "summary": "ตรวจพบว่าโครงสร้างทำงานได้และมีการคุมขอบเขต" if healthy else "มีประเด็นที่ต้องติดตามก่อนเรียกว่าพร้อมเต็มที่",
            "limitations": "รายงานนี้ช่วยตรวจความครบและสถานะจากข้อมูลในโครงการ แต่ไม่สามารถรับประกันว่าไม่มีช่องโหว่ทุกชนิดได้",
            "checks": checks,
        }
