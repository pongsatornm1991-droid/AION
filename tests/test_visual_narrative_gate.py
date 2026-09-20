import unittest

from brain.visual_narrative_gate import VisualNarrativeGate


class VisualNarrativeGateTests(unittest.TestCase):
    def _episode(self):
        scenes = [
            {"beat": "hook"}, {"beat": "mechanism"}, {"beat": "takeaway"},
        ]
        return {
            "scenes": scenes,
            "visual_direction": {"aion_role": "contextual-guide"},
            "visual_narrative": VisualNarrativeGate.plan("Why light makes a rainbow", scenes),
        }

    def test_accepts_one_visual_metaphor_with_a_real_story_step_per_scene(self):
        self.assertTrue(VisualNarrativeGate.assess(self._episode())["eligible"])

    def test_rejects_missing_cover_focus_and_repeated_progression(self):
        episode = self._episode()
        episode["visual_narrative"]["cover"] = {}
        episode["visual_narrative"]["scene_progression"] = ["hook", "hook", "takeaway"]
        report = VisualNarrativeGate.assess(episode)
        self.assertFalse(report["eligible"])
        self.assertIn("missing-single-focus-cover-plan", report["reasons"])
        self.assertIn("each-scene-needs-a-distinct-story-step", report["reasons"])
