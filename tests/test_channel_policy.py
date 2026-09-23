import unittest

from brain.channel_policy import ChannelPolicy


class ChannelPolicyTests(unittest.TestCase):
    def test_current_brand_and_daily_release_contract_are_single_source(self):
        policy = ChannelPolicy().load()
        self.assertEqual("Wait, How?", policy["brand"]["channel_name"])
        self.assertEqual("@waithow-aion", policy["brand"]["handle"])
        self.assertEqual(list(range(7)), policy["publishing"]["shorts_days"])
        self.assertEqual("20:30", policy["publishing"]["shorts_time"])
        self.assertEqual(7, policy["publishing"]["shorts_buffer_target"])
        self.assertEqual("aion-neon-diorama-3d-v1", policy["production"]["automatic_release_visual_style"])


if __name__ == "__main__":
    unittest.main()
