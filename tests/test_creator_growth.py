import unittest

from brain.creator_growth import CreatorGrowthGate


class CreatorGrowthTests(unittest.TestCase):
    def test_default_plan_makes_the_growth_contract_inspectable(self):
        plan = CreatorGrowthGate.default_plan("octopus colour change", "Viewers learn the mechanism.")
        report = CreatorGrowthGate.assess({"growth_plan": plan})
        self.assertTrue(report["eligible"])
        self.assertEqual(2, plan["hook_seconds"])

    def test_rejects_an_episode_without_a_reason_to_follow(self):
        plan = CreatorGrowthGate.default_plan("a subject", "a benefit")
        plan["follow_reason"] = ""
        report = CreatorGrowthGate.assess({"growth_plan": plan})
        self.assertIn("missing-follow-reason", report["reasons"])
