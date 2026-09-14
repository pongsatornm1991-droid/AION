import json
import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from brain.operations_control import OperationsControlTower


class OperationsControlTowerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "content" / "images").mkdir(parents=True)
        (self.root / ".github" / "workflows").mkdir(parents=True)
        for path in ("main.py", "run_tests.py", "brain/autonomy_policy.py", "tools/dashboard.py",
                     ".github/workflows/tests.yml", ".github/workflows/system-reliability.yml"):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
        self.memory = MemoryEngine(self.root / "memory")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pending_work_is_visible_with_automatic_recovery(self):
        self.memory.remember("pending_visual_content", json.dumps({"caption": "A fresh visual"}), "action")
        report = OperationsControlTower(self.memory, self.root).snapshot()
        self.assertEqual("ภาพ Instagram", report["work_now"][0]["name"])
        self.assertIn("ไม่สร้างโพสต์ซ้ำ", report["recovery_policy"])

    def test_delivery_gaps_are_visible_not_claimed_as_success(self):
        report = OperationsControlTower(self.memory, self.root).snapshot()
        names = {item["name"] for item in report["blockers"]}
        self.assertIn("Facebook", names)
        self.assertEqual("attention", report["status"])

