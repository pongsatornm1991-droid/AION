import tempfile
import unittest
from pathlib import Path

from brain.self_repair import SafeRepairAgent


class SafeRepairAgentTests(unittest.TestCase):
    def test_creates_only_recoverable_work_directories(self):
        with tempfile.TemporaryDirectory() as root:
            report = SafeRepairAgent(root, Path(root) / "memory").run_once()
            self.assertEqual("repaired", report["stage"])
            self.assertTrue((Path(root) / "content" / "images").is_dir())
            self.assertIn("ไม่แก้โค้ด", report["boundary"])

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            agent = SafeRepairAgent(root, Path(root) / "memory")
            agent.run_once()
            self.assertEqual("checked-no-repair-needed", agent.run_once()["stage"])
