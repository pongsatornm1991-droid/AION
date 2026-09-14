import tempfile
import unittest

from brain.memory import MemoryEngine
from brain.publication_cadence import PublicationCadence
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class PublicationCadenceTests(unittest.TestCase):
    def test_successful_feed_post_uses_that_platform_daily_slot(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root=root)
            registry = ToolRegistry()
            registry.register("post_to_facebook", lambda message: {"id": "safe"}, ActionLevel.HIGH_RISK)
            lifecycle = ToolLifecycle(memory, registry=registry)
            proposed = lifecycle.propose("post_to_facebook", {"message": "hello"}, source="test")
            approved = lifecycle.approve(proposed["id"], "reviewer")
            lifecycle.execute(approved["id"])
            self.assertFalse(PublicationCadence(memory).has_slot("facebook"))
            self.assertTrue(PublicationCadence(memory).has_slot("instagram"))
