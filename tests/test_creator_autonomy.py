import json
import tempfile
import unittest

from brain.creator_autonomy import CreatorAutonomy
from brain.curiosity import CuriosityEngine
from brain.memory import MemoryEngine


class CreatorAutonomyTests(unittest.TestCase):
    def test_creates_intention_from_its_open_question_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            question = CuriosityEngine(memory).raise_question(
                "How did the first cells arise?", "Compare at least two cited scientific sources.",
                priority=4, tags=["science", "learning"],
            )
            engine = CreatorAutonomy(memory)
            first = engine.choose_once()
            self.assertEqual("intention-created", first["stage"])
            intention = first["intention"]
            self.assertEqual("curiosity", intention["origin"])
            self.assertEqual(question["id"], intention["origin_memory_id"])
            self.assertIn("visual", intention["creative_shape"])
            self.assertTrue(intention["why_now"])
            self.assertIn("uncertainty", intention["audience_promise"])
            second = engine.choose_once()
            self.assertEqual("already-intending", second["stage"])
            self.assertEqual(1, len(memory.all("creative_intentions")))

    def test_originate_one_modest_first_question_when_the_mind_is_empty(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            result = CreatorAutonomy(memory).choose_once()
            self.assertEqual("intention-created", result["stage"])
            self.assertEqual("curiosity", result["intention"]["origin"])
            self.assertEqual(1, len(memory.all("questions")))
            self.assertEqual("already-intending", CreatorAutonomy(memory).choose_once()["stage"])

    def test_dashboard_exposes_current_intention(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "creative_intentions", json.dumps({"status": "pending", "topic": "A question AION chose"}),
                "decision", source="aion-creator-autonomy",
            )
            snapshot = CreatorAutonomy(memory).snapshot()
            self.assertEqual("intending", snapshot["status"])
            self.assertEqual("A question AION chose", snapshot["current"]["topic"])
