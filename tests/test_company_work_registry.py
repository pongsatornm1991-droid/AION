import json
import tempfile
import unittest
from pathlib import Path

from brain.company_work_registry import CompanyWorkRegistry


class CompanyWorkRegistryTests(unittest.TestCase):
    def test_maps_published_workflow_state_to_owning_department(self):
        with tempfile.TemporaryDirectory() as root:
            public = Path(root) / "public"; public.mkdir()
            (public / "aion-workflow-status.json").write_text(json.dumps({
                "generated_at": "2026-09-12T00:00:00Z",
                "groups": [{"items": [{"file": "reel-cycle.yml", "status_class": "success"}]}],
            }), encoding="utf-8")
            result = CompanyWorkRegistry(root).snapshot()
            publishing = next(x for x in result["departments"] if x["department"] == "publishing")
            self.assertEqual("success", publishing["state"])
            self.assertEqual("2026-09-12T00:00:00Z", result["generated_at"])
