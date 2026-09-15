import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.work_queue import WorkQueue


class WorkQueueTests(unittest.TestCase):
    def test_same_lane_and_key_creates_one_durable_work_card(self):
        with tempfile.TemporaryDirectory() as root:
            queue = WorkQueue(MemoryEngine(root))
            first = queue.ensure("research-to-story", "q1", "Research", "Ice", "Story", related=["q1"])
            second = queue.ensure("research-to-story", "q1", "Research", "Ice", "Story")
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["card"]["task_id"], second["card"]["task_id"])

    def test_transition_keeps_one_identity_and_exposes_current_owner(self):
        with tempfile.TemporaryDirectory() as root:
            queue = WorkQueue(MemoryEngine(root))
            card = queue.ensure("research-to-story", "q2", "Research", "Desert ice", "Story")["card"]
            result = queue.transition(card["task_id"], "in-progress", owner="Story", next_owner="Visual")
            self.assertTrue(result["changed"])
            current = queue.snapshot()["active"][0]
            self.assertEqual("Story", current["owner"])
            self.assertEqual("Visual", current["next_owner"])

    def test_terminal_card_cannot_be_reopened_by_a_retry(self):
        with tempfile.TemporaryDirectory() as root:
            queue = WorkQueue(MemoryEngine(root))
            card = queue.ensure("social-reel", "r1", "Publishing", "AION Reel", "Audience")["card"]
            queue.transition(card["task_id"], "completed")
            retry = queue.transition(card["task_id"], "in-progress")
            self.assertFalse(retry["changed"])
            self.assertEqual("completed", retry["card"]["status"])
