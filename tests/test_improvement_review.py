import tempfile
import unittest

from brain.improvement_review import ImprovementReview
from brain.memory import MemoryEngine


class ImprovementReviewTests(unittest.TestCase):
    def test_queue_autonomously_marks_a_bounded_experiment(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            proposal = memory.remember("self_improvement", "Improve the opening hook.", memory_type="observation", source="test", importance=3)
            cycle = ImprovementReview(memory)
            queued = cycle.queue_once()
            self.assertEqual("approved-for-experiment", queued["stage"])
            self.assertEqual(proposal["id"], queued["review"]["proposal_id"])

    def test_auto_path_queues_a_plan_without_sending_a_button(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("self_improvement", "Improve the opening hook.", memory_type="observation", source="test", importance=3)
            result = ImprovementReview(memory).send_pending_once()
            self.assertEqual("experiment-queued", result["stage"])
            self.assertEqual("queued", result["plan"]["stage"])
