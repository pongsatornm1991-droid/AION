"""Offline tests for the official OpenAI Responses API provider."""

import os
import unittest
from unittest import mock

from providers.openai import OpenAIProvider


class _Response:
    status_code = 200

    def __init__(self, payload=None):
        self.payload = payload or {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": " draft "}],
            }]
        }

    def json(self):
        return self.payload


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        self.environment = mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "test-model",
        }, clear=False)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    @mock.patch("requests.post")
    def test_uses_native_responses_api_without_server_storage(self, post):
        post.return_value = _Response()
        provider = OpenAIProvider()

        self.assertEqual(provider.generate("hello"), "draft")
        self.assertEqual(
            post.call_args.args[0],
            "https://api.openai.com/v1/responses",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )
        self.assertEqual(post.call_args.kwargs["json"], {
            "model": "test-model",
            "input": "hello",
            "store": False,
        })

    @mock.patch("requests.post")
    def test_gpt5_defaults_to_low_reasoning_effort_to_cap_hidden_output_tokens(self, post):
        # 2026-10-03: gpt-5 output was the largest line of the owner's bill.
        post.return_value = _Response()
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-5"}):
            OpenAIProvider().generate("hello")
        self.assertEqual({"effort": "low"}, post.call_args.kwargs["json"]["reasoning"])

    @mock.patch("requests.post")
    def test_reasoning_effort_can_be_overridden_or_disabled(self, post):
        post.return_value = _Response()
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-5-mini", "OPENAI_REASONING_EFFORT": "high"}):
            OpenAIProvider().generate("hello")
        self.assertEqual({"effort": "high"}, post.call_args.kwargs["json"]["reasoning"])
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-5", "OPENAI_REASONING_EFFORT": ""}):
            OpenAIProvider().generate("hello")
        self.assertNotIn("reasoning", post.call_args.kwargs["json"])

    @mock.patch("requests.post")
    def test_models_outside_the_gpt5_family_never_receive_a_reasoning_setting(self, post):
        post.return_value = _Response()
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4.1-mini"}):
            OpenAIProvider().generate("hello")
        self.assertNotIn("reasoning", post.call_args.kwargs["json"])

    def test_requires_api_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                OpenAIProvider()

    def test_extracts_all_output_text_parts(self):
        payload = {
            "output": [{
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "first"},
                    {"type": "refusal", "refusal": "not used"},
                    {"type": "output_text", "text": "second"},
                ],
            }]
        }
        self.assertEqual(
            OpenAIProvider._output_text(payload),
            "first\nsecond",
        )

    @mock.patch("requests.post")
    def test_api_errors_do_not_expose_authorization_header(self, post):
        post.return_value = _Response({
            "error": {"message": "invalid request"}
        })
        post.return_value.status_code = 400

        with self.assertRaisesRegex(RuntimeError, "invalid request"):
            OpenAIProvider().generate("hello")

    def test_main_provider_factory_selects_official_openai(self):
        from main import build_provider

        with mock.patch.dict(os.environ, {"AI_PROVIDER": "openai"}, clear=False):
            self.assertIsInstance(build_provider(), OpenAIProvider)


if __name__ == "__main__":
    unittest.main()
