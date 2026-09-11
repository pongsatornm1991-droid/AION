import tempfile
import unittest

from brain.improvement_review import ImprovementReview
from brain.memory import MemoryEngine


class ImprovementReviewTests(unittest.TestCase):
    def test_queue_then_approve_only_marks_an_experiment(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            proposal = memory.remember("self_improvement", "Improve the opening hook.", memory_type="observation", source="test", importance=3)
            cycle = ImprovementReview(memory)
            queued = cycle.queue_once()
            self.assertEqual("awaiting-owner", queued["stage"])
            result = cycle.decide(queued["review"]["review_id"], True)
            self.assertEqual("approved-for-experiment", result["stage"])
            self.assertEqual(proposal["id"], result["review"]["proposal_id"])
