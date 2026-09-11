import json
import tempfile
import unittest
from brain.content_experiment import ContentExperimentExecutor
from brain.memory import MemoryEngine

class ContentExperimentTests(unittest.TestCase):
    def test_assigns_balanced_variants_and_waits_for_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("content_experiment_plans", json.dumps({"review_id":"r1", "status":"queued", "sample_size":4}), memory_type="experiment", source="test", importance=4)
            cycle = ContentExperimentExecutor(memory)
            self.assertEqual("control", cycle.assign_next("a")["variant"])
            self.assertEqual("experiment", cycle.assign_next("b")["variant"])
            self.assertEqual("waiting-for-attributed-outcomes", cycle.evaluate_once()["stage"])

    def test_evaluates_only_after_four_attributed_outcomes(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("content_experiment_plans", json.dumps({"review_id":"r1", "status":"queued", "sample_size":4}), memory_type="experiment", source="test", importance=4)
            cycle = ContentExperimentExecutor(memory)
            for idx in range(4):
                content_id = f"c{idx}"
                cycle.assign_next(content_id)
                memory.remember("content_attribution", json.dumps({"content_id":content_id, "like_count":idx, "comments_count":idx}), memory_type="observation", source="test", importance=3)
            self.assertEqual("evaluated", cycle.evaluate_once()["stage"])
            plan = json.loads(memory.all("content_experiment_plans")[0]["content"])
            self.assertEqual("evaluated", plan["status"])
            self.assertEqual("no-active-experiment", cycle.evaluate_once()["stage"])
