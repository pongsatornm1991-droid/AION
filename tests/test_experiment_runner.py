import json
import tempfile
import unittest
from brain.experiment_runner import ExperimentRunner
from brain.memory import MemoryEngine

class ExperimentRunnerTests(unittest.TestCase):
    def test_queues_one_bounded_plan_only_after_owner_approval(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("improvement_reviews", json.dumps({"review_id": "r1", "proposal_id": "p1", "status": "approved-for-experiment"}), memory_type="decision", source="test", importance=4)
            runner = ExperimentRunner(memory)
            report = runner.queue_once()
            self.assertEqual("queued", report["stage"])
            self.assertEqual(4, report["plan"]["sample_size"])
            self.assertEqual("no-approved-proposal", runner.queue_once()["stage"])
