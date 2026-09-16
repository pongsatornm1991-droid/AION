import unittest

from brain.visual_story_policy import VisualStoryPolicy


class VisualStoryPolicyTests(unittest.TestCase):
    def test_subject_first_fast_cut_episode_passes(self):
        report = VisualStoryPolicy.validate_episode({
            "pacing_policy": VisualStoryPolicy.VERSION,
            "scene_seconds": 5,
            "target_duration_seconds": 60,
            "visual_identity": {"version": VisualStoryPolicy.IDENTITY_VERSION},
            "visual_direction": {"focus": "subject-first", "aion_role": "contextual-guide", "aion_frame_share_max": 0.20},
        })
        self.assertTrue(report["eligible"])

    def test_rejects_hero_framing_and_slow_scenes(self):
        report = VisualStoryPolicy.validate_episode({
            "pacing_policy": VisualStoryPolicy.VERSION,
            "scene_seconds": 8,
            "target_duration_seconds": 60,
            "visual_identity": {"version": VisualStoryPolicy.IDENTITY_VERSION},
            "visual_direction": {"focus": "aion-hero", "aion_role": "lead", "aion_frame_share_max": 0.6},
        })
        self.assertFalse(report["eligible"])
        self.assertIn("scene-duration-must-be-5-seconds", report["reasons"])

    def test_allows_a_story_justified_guest_guide_role(self):
        report = VisualStoryPolicy.validate_episode({
            "pacing_policy": VisualStoryPolicy.VERSION,
            "scene_seconds": 5,
            "target_duration_seconds": 60,
            "visual_identity": {"version": VisualStoryPolicy.IDENTITY_VERSION},
            "visual_direction": {
                "focus": "subject-first", "aion_role": "contextual-guide",
                "aion_frame_share_max": 0.28,
                "aion_presence_rationale": "A recurring guide helps young viewers follow a location-changing journey.",
            },
        })
        self.assertTrue(report["eligible"])

    def test_rejects_current_short_without_approved_visual_identity(self):
        report = VisualStoryPolicy.validate_episode({
            "pacing_policy": VisualStoryPolicy.VERSION,
            "scene_seconds": 5,
            "target_duration_seconds": 60,
            "visual_direction": {"focus": "subject-first", "aion_role": "contextual-guide", "aion_frame_share_max": 0.20},
        })
        self.assertFalse(report["eligible"])
        self.assertIn("missing-approved-aion-visual-identity", report["reasons"])
