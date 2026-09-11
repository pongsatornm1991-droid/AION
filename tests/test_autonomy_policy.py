import unittest
from pathlib import Path

from brain.autonomy_policy import AutonomyPolicy


class AutonomyPolicyTests(unittest.TestCase):
    def test_project_delegates_public_publishing_but_protects_accounts_and_money(self):
        root = Path(__file__).resolve().parents[1]
        policy = AutonomyPolicy(root)
        self.assertTrue(policy.public_publishing_enabled)
        protected = " ".join(policy.data["chair_approval_required"])
        self.assertIn("เงิน", protected)
        self.assertIn("สิทธิ์", protected)
