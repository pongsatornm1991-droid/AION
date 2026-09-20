import unittest

from brain.fact_first_visual_gate import FactFirstVisualGate


class FactFirstVisualGateTests(unittest.TestCase):
    def _episode(self):
        scenes = [
            {"n": 1, "beat": "hook"}, {"n": 2, "beat": "evidence-one"},
            {"n": 3, "beat": "mechanism"}, {"n": 4, "beat": "connection"},
            {"n": 5, "beat": "boundary"}, {"n": 6, "beat": "takeaway"},
        ]
        sources = [
            {"observation": "Sunlight enters water droplets and bends."},
            {"observation": "Different colours bend by different amounts."},
        ]
        return {"scenes": scenes, "fact_first_visual": FactFirstVisualGate.plan("Why rainbows appear after rain", sources, scenes)}

    def test_accepts_a_factual_anchor_mechanism_and_creative_boundary(self):
        self.assertTrue(FactFirstVisualGate.assess(self._episode())["eligible"])

    def test_rejects_a_pretty_plan_without_traceable_claims(self):
        episode = self._episode()
        episode["fact_first_visual"]["reality_anchor"]["evidence_claims"] = []
        report = FactFirstVisualGate.assess(episode)
        self.assertFalse(report["eligible"])
        self.assertIn("missing-two-factual-visual-claims", report["reasons"])
