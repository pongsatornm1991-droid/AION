"""One inspectable work register across AION Company departments.

Workflow files remain the executors. This registry only reads their published
status and maps it to the department that owns the work, so it cannot trigger
an external action or conceal a failed job.
"""

import json
from pathlib import Path

from brain.company_operations import CompanyOperations


class CompanyWorkRegistry:
    """Build a single operational view from the workflow-health artifact."""

    LABELS = {
        "success": "สำเร็จล่าสุด",
        "running": "กำลังทำงาน",
        "failure": "ต้องตรวจสอบ",
        "cancelled": "ยกเลิก",
        "partial": "ทำงานได้บางส่วน — ยังมีงานรอยืนยัน",
        "unknown": "ยังไม่มีผลยืนยัน",
    }

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _workflow_status(self):
        path = self.root / "public" / "aion-workflow-status.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}, None
        statuses = {}
        for group in data.get("groups") or []:
            for item in group.get("items") or []:
                if item.get("file"):
                    statuses[item["file"]] = item
        return statuses, data.get("generated_at")

    def snapshot(self):
        statuses, generated_at = self._workflow_status()
        work = []
        for department, _, workflows in CompanyOperations.DEPARTMENTS:
            items = []
            for path in workflows:
                key = Path(path).name
                item = statuses.get(key, {})
                state = item.get("status_class", "unknown")
                items.append({
                    "workflow": key,
                    "state": state,
                    "label": self.LABELS.get(state, state),
                    "url": item.get("html_url"),
                    "updated_at": item.get("created_at"),
                })
            states = {item["state"] for item in items}
            # A department must not be reported as fully successful merely
            # because one of its workflows succeeded while another has never
            # reported a result.  This is especially important for new
            # workflows, where an absent run is operationally meaningful.
            overall = (
                "failure" if "failure" in states else
                "running" if "running" in states else
                "partial" if "success" in states and "unknown" in states else
                "success" if "success" in states else
                "cancelled" if "cancelled" in states else
                "unknown"
            )
            work.append({
                "department": department,
                "state": overall,
                "label": self.LABELS[overall],
                "workflows": items,
            })
        return {"generated_at": generated_at, "departments": work}
