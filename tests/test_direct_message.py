import os
import shutil
import tempfile
import unittest
from unittest import mock

from brain.comment_reply import CommentReplyGenerator
from brain.direct_message import DirectMessageCycle
from brain.memory import MemoryEngine
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class Provider:
    def generate(self, prompt):
        return "สวัสดีครับ ขอบคุณที่ส่งข้อความมาคุยกัน"


class DirectMessageTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.memory = MemoryEngine(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def cycle(self):
        registry = ToolRegistry()
        registry.register("reply_to_facebook_message", lambda recipient_id, message: {"id": "sent"},
                          ActionLevel.COMMENT_REPLY, "reply")
        return DirectMessageCycle(
            self.memory, CommentReplyGenerator(Provider()),
            ToolLifecycle(self.memory, registry), "reply_to_facebook_message", "facebook",
        )

    def test_stays_off_until_meta_messaging_permission_is_enabled(self):
        with mock.patch.dict(os.environ, {"AION_MESSAGING_ENABLED": "false"}):
            self.assertEqual(self.cycle().run_once([])["stage"], "permission-pending")

    def test_answers_and_deduplicates_an_incoming_message(self):
        item = {"id": "m1", "message": "สวัสดี", "recipient_id": "u1",
                "from_id": "u1", "created_time": "2026-09-08T01:00:00+0000"}
        with mock.patch.dict(os.environ, {"AION_MESSAGING_ENABLED": "true"}):
            cycle = self.cycle()
            self.assertTrue(cycle.run_once([item])["handled"])
            self.assertEqual(cycle.run_once([item])["stage"], "no-messages")

    def test_reports_the_missing_facebook_permission_clearly(self):
        report = self.cycle()._permission_result(
            "Facebook Graph API error (OAuthException, code 200): Requires permission: pages_messaging"
        )
        self.assertEqual(report["stage"], "permission-required")
        self.assertEqual(report["permission"], "pages_messaging")
