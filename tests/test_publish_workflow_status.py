import unittest

from tools.publish_workflow_status import pill_for


class WorkflowStatusTests(unittest.TestCase):
    def test_skipped_monitor_is_a_healthy_noop(self):
        self.assertEqual(
            ("success", "ไม่มีเหตุให้ดำเนินการ"),
            pill_for({"status": "completed", "conclusion": "skipped"}),
        )

    def test_failed_workflow_remains_attention_worthy(self):
        self.assertEqual(
            ("failure", "ล้มเหลว"),
            pill_for({"status": "completed", "conclusion": "failure"}),
        )
