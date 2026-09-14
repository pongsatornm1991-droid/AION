import tempfile
import unittest
from pathlib import Path

from brain.continuity_guard import ContinuityGuard


class ContinuityGuardTests(unittest.TestCase):
    def test_reports_local_memory_as_waiting_without_claiming_a_backup(self):
        with tempfile.TemporaryDirectory() as root:
            report = ContinuityGuard(root, Path(root) / "memory").snapshot()
            memory = next(item for item in report["checks"] if item["name"] == "ประวัติงานและความจำ")
            self.assertEqual("waiting", memory["state"])

    def test_recovery_statement_never_includes_credentials(self):
        with tempfile.TemporaryDirectory() as root:
            report = ContinuityGuard(root).snapshot()
            self.assertIn("ไม่แตะข้อมูลรับรอง", report["recovery"])
