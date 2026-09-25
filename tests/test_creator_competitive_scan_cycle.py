import json
import tempfile
import unittest
from datetime import datetime, timezone

from brain.creator_competitive_scan_cycle import CATEGORY, CreatorCompetitiveScanCycle
from brain.memory import MemoryEngine

SUCCESS_REPORT = {
    "generated_at": "2026-09-27T02:15:00+00:00", "ok": True,
    "results": [{"query": "q", "video_id": f"v{i}", "title": f"Title {i}", "channel": "C",
                 "url": f"https://www.youtube.com/watch?v=v{i}", "published_at": None, "view_count": 100 - i}
                for i in range(20)],
}

FAILURE_REPORT = {"generated_at": "2026-09-27T02:15:00+00:00", "ok": False, "error": "no api key", "results": []}


class CreatorCompetitiveScanCycleTests(unittest.TestCase):
    def test_first_scan_of_the_day_is_saved_and_trimmed_to_top_results(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            cycle = CreatorCompetitiveScanCycle(memory, scan_fn=lambda **_: SUCCESS_REPORT)
            report = cycle.scan_once(now=datetime(2026, 9, 27, tzinfo=timezone.utc))
            self.assertEqual(report["stage"], "scanned")
            self.assertTrue(report["saved"])
            record = json.loads(memory.all(CATEGORY)[0]["content"])
            self.assertEqual(len(record["results"]), 15)

    def test_a_second_run_the_same_day_is_skipped_not_duplicated(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            cycle = CreatorCompetitiveScanCycle(memory, scan_fn=lambda **_: SUCCESS_REPORT)
            same_day = datetime(2026, 9, 27, tzinfo=timezone.utc)
            cycle.scan_once(now=same_day)
            second = cycle.scan_once(now=same_day)
            self.assertEqual(second["stage"], "already-scanned-today")
            self.assertFalse(second["saved"])
            self.assertEqual(len(memory.all(CATEGORY)), 1)

    def test_a_provider_failure_is_recorded_truthfully_not_hidden(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            cycle = CreatorCompetitiveScanCycle(memory, scan_fn=lambda **_: FAILURE_REPORT)
            report = cycle.scan_once(now=datetime(2026, 9, 27, tzinfo=timezone.utc))
            self.assertEqual(report["stage"], "scan-failed")
            record = json.loads(memory.all(CATEGORY)[0]["content"])
            self.assertEqual(record["error"], "no api key")


if __name__ == "__main__":
    unittest.main()
