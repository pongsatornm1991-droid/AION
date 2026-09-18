import json
import unittest

from brain.aion_creative_director import AionCreativeDirector


class _Provider:
    def generate(self, _prompt):
        return json.dumps({
            "premise": "A glass tide carries archived questions toward a future shore.",
            "world": "memory coast", "mood": "quiet discovery",
            "palette_and_material": "blue hour and translucent glass",
            "aion_role": "a small observer at the edge",
            "appearance_choice": "a quiet traveller in weatherproof slate layers with a cyan compass pin",
            "rendering_rule": "Original expressive illustration with no named references.",
        })


class AionCreativeDirectorTests(unittest.TestCase):
    def test_accepts_aion_model_creative_choice(self):
        result = AionCreativeDirector.propose("Ocean memory", "Learn carefully", provider=_Provider())
        self.assertEqual("aion-model-deliberation", result["origin"])
        self.assertEqual("memory coast", result["world"])
        self.assertIn("traveller", result["appearance_choice"])
        self.assertIn("2D animated-documentary", result["rendering_rule"])

    def test_falls_back_without_a_provider(self):
        result = AionCreativeDirector.propose("Ocean memory", "Learn carefully")
        self.assertEqual("bounded-fallback", result["origin"])
