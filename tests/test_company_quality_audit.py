import json
import tempfile
import unittest
from pathlib import Path

from brain.company_quality_audit import CompanyQualityAudit
from brain.company_operations import CompanyOperations


class CompanyQualityAuditTests(unittest.TestCase):
    def test_flags_missing_structure_instead_of_claiming_health(self):
        with tempfile.TemporaryDirectory() as root:
            result = CompanyQualityAudit(root).snapshot()
            self.assertEqual("needs-attention", result["status"])
            structure = next(item for item in result["checks"] if item["id"] == "structure")
            self.assertEqual("attention", structure["state"])

    def test_reports_healthy_only_when_structure_policy_and_workflows_are_complete(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            for _, modules, workflows in CompanyOperations.DEPARTMENTS:
                for name in (*modules, *workflows):
                    path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("ok", encoding="utf-8")
            (root / "config").mkdir()
            (root / "config" / "aion_authority.json").write_text(json.dumps({
                "public_publishing": {"enabled": True},
                "chair_approval_required": ["เงิน", "สิทธิ์บัญชี", "ข้อมูลรับรอง"],
            }), encoding="utf-8")
            all_workflows = sorted({Path(name).name for _, _, flows in CompanyOperations.DEPARTMENTS for name in flows})
            (root / "public").mkdir()
            (root / "public" / "aion-workflow-status.json").write_text(json.dumps({
                "groups": [{"items": [{"file": name, "status_class": "success"} for name in all_workflows]}],
            }), encoding="utf-8")
            self.assertEqual("healthy", CompanyQualityAudit(root).snapshot()["status"])
