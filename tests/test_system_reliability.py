import tempfile
import unittest
from pathlib import Path

from brain.system_reliability import SystemReliability


class SystemReliabilityTests(unittest.TestCase):
    def test_reports_missing_required_paths_without_mutating(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = SystemReliability(root).snapshot()
            self.assertEqual(snapshot["status"], "needs-attention")
            self.assertIn("main.py", snapshot["missing"])
            self.assertIn("ไม่แก้โค้ด", snapshot["boundary"])
