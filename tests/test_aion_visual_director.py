import unittest

from brain.aion_visual_director import AionVisualDirector


class AionVisualDirectorTests(unittest.TestCase):
    def test_chooses_a_story_world_from_the_subject(self):
        direction = AionVisualDirector.direct("How does an octopus change color?")
        self.assertEqual("ocean", direction["world"])
        self.assertEqual(AionVisualDirector.VERSION, direction["id"])

    def test_unknown_subject_stays_original_and_grounded(self):
        direction = AionVisualDirector.direct("Why is gravity strange?")
        self.assertEqual("curiosity-atlas", direction["world"])
        self.assertIn("Never imitate", direction["rendering_rule"])
