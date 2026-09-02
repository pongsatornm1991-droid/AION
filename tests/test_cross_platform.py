import json
import os
import tempfile
import unittest
from unittest import mock

from brain.cross_platform import append_invitation, invitation, platform_urls, should_invite
from brain.memory import MemoryEngine


class CrossPlatformTests(unittest.TestCase):
    def test_registry_reads_static_and_environment_urls(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "platforms.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"platforms": {"youtube": {"url": "https://youtube.test/aion"}, "instagram": {"url_env": "AION_TEST_IG"}}}, handle)
            with mock.patch.dict(os.environ, {"AION_TEST_IG": "https://instagram.test/aion"}):
                self.assertEqual(platform_urls(path)["instagram"], "https://instagram.test/aion")

    def test_invitation_is_added_only_every_fourth_platform_post(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            for n in range(3):
                memory.remember("social_language_log", f"platform=instagram; action={n}", memory_type="action", source="test")
            self.assertTrue(should_invite(memory, "instagram"))
            message = append_invitation("One discovery.", "instagram", memory)
            self.assertIn("YouTube", message)
            memory.remember("social_language_log", "platform=instagram; action=4", memory_type="action", source="test")
            self.assertEqual("", invitation("instagram", memory))

