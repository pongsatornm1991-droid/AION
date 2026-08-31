"""Offline tests for the OpenAI-compatible provider adapter."""

import os
import unittest
from unittest import mock

from providers.openai_compatible import OpenAICompatibleProvider


class _Response:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "  draft  "}}]}


class OpenAICompatibleProviderTests(unittest.TestCase):

    def setUp(self):
        self.environment = mock.patch.dict(os.environ, {
            "OPENAI_COMPATIBLE_BASE_URL": "http://localhost:18888/v1",
            "OPENAI_COMPATIBLE_API_KEY": "test-key",
            "OPENAI_COMPATIBLE_MODEL": "openchat_3.6",
        }, clear=False)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    @mock.patch("requests.post")
    def test_uses_openai_chat_completions_protocol(self, post):
        post.return_value = _Response()
        provider = OpenAICompatibleProvider()

        self.assertEqual(provider.generate("hello"), "draft")
        url = post.call_args.args[0]
        self.assertEqual(url, "http://localhost:18888/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "openchat_3.6")

    def test_requires_an_endpoint(self):
        with mock.patch.dict(os.environ, {"OPENAI_COMPATIBLE_BASE_URL": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                OpenAICompatibleProvider()
