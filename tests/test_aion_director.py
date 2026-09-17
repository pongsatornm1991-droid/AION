import unittest

from brain.aion_director import AionDirector
from brain.watchability_gate import WatchabilityGate


class AionDirectorTests(unittest.TestCase):
    def _episode(self):
        return {
            "audience_promise": "Viewers understand one evidence-led idea through clear scenes.",
            "scene_seconds": 5,
            "sources": [{"url": "https://example.test"}],
            "visual_direction": {"aion_role": "contextual-guide"},
            "visual_identity": {"version": "aion-stylized-guide-real-world-v1"},
            "scenes": [
                {"n": 1, "visual": "A surprising real subject fills the frame.", "narration": "Here is the surprising question that this story will answer."},
                {"n": 2, "visual": "A new evidence angle explains the mechanism.", "narration": "This is the documented clue that lets us understand the answer."},
                {"n": 3, "visual": "A wide closing view returns to the real subject.", "narration": "Follow for the next evidence-led question we can investigate together."},
            ],
        }

    def test_director_plan_makes_hook_and_ending_inspectable(self):
        plan = AionDirector.plan(self._episode())
        self.assertEqual("director-plan-v1", plan["version"])
        self.assertIn("surprising question", plan["hook"]["narration"])
        self.assertIn("silent image", plan["ending"]["viewer_reason_to_return"])

    def test_watchability_blocks_silent_or_repeated_storyboards(self):
        episode = self._episode()
        episode["scenes"][1]["narration"] = ""
        episode["scenes"][2]["visual"] = episode["scenes"][0]["visual"]
        report = WatchabilityGate.assess_storyboard(episode)
        self.assertFalse(report["eligible"])
        self.assertIn("repeated-visual-direction", report["reasons"])
        self.assertTrue(any(reason.startswith("silent-storyboard-scenes") for reason in report["reasons"]))
