import json
import tempfile
import unittest
from pathlib import Path

from brain.company_work_registry import CompanyWorkRegistry
from brain.company_operations import CompanyOperations


class CompanyWorkRegistryTests(unittest.TestCase):
    @staticmethod
    def _publishing_workflows():
        return next(workflows for department, _, workflows in CompanyOperations.DEPARTMENTS
                    if department == "publishing")

    def test_maps_published_workflow_state_to_owning_department(self):
        with tempfile.TemporaryDirectory() as root:
            public = Path(root) / "public"; public.mkdir()
            first = Path(self._publishing_workflows()[0]).name
            (public / "aion-workflow-status.json").write_text(json.dumps({
                "generated_at": "2026-09-12T00:00:00Z",
                "groups": [{"items": [{"file": first, "status_class": "success"}]}],
            }), encoding="utf-8")
            result = CompanyWorkRegistry(root).snapshot()
            publishing = next(x for x in result["departments"] if x["department"] == "publishing")
            self.assertEqual("partial", publishing["state"])
            self.assertEqual("2026-09-12T00:00:00Z", result["generated_at"])

    def test_requires_all_workflows_to_report_before_success(self):
        with tempfile.TemporaryDirectory() as root:
            public = Path(root) / "public"; public.mkdir()
            (public / "aion-workflow-status.json").write_text(json.dumps({
                "groups": [{"items": [
                    {"file": Path(path).name, "status_class": "success"}
                    for path in self._publishing_workflows()
                ]}],
            }), encoding="utf-8")
            result = CompanyWorkRegistry(root).snapshot()
            publishing = next(x for x in result["departments"] if x["department"] == "publishing")
            self.assertEqual("success", publishing["state"])
