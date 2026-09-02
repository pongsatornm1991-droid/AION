import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.visual_mood import MOOD_PALETTE, select_visual_mood, state_council


class VisualMoodTests(unittest.TestCase):
    def test_council_exposes_a_palette_for_every_state(self):
        council = state_council(
            {"lessons": 1, "questions": 4, "beliefs": 0, "goals": 0,
             "reflections": 0, "self_narrative": 0},
            {"published": 0},
        )
        self.assertEqual("curiosity", council["dominant"])
        self.assertEqual(MOOD_PALETTE["curiosity"]["color"], council["palette"]["color"])
        self.assertTrue(all(state["color"] for state in council["states"]))

    def test_memory_selects_a_repeatable_visual_mood(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("beliefs", "Knowledge should remain revisable.", "belief")
            memory.remember("goals", "Learn with evidence.", "goal")
            mood = select_visual_mood(memory)
        self.assertEqual("ego", mood["key"])
        self.assertEqual("#62e8d2", mood["color"])


if __name__ == "__main__":
    unittest.main()
