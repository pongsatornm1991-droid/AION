"""Offline tests for tools/telegram.py.

Mocks requests.post entirely -- this suite must never make a live call
to the Telegram Bot API, per the project's rule that unit tests never
depend on a live external service.
"""

import os
import unittest
from unittest import mock

from tools.telegram import TELEGRAM_API_BASE, send_telegram_message


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}

    def json(self):
        return self._payload


class SendTelegramMessageTests(unittest.TestCase):

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "test-bot-token", "TELEGRAM_CHAT_ID": "12345"},
            clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.telegram.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_empty_text_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                send_telegram_message("   ")
            mock_post.assert_not_called()

    def test_missing_bot_token_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    send_telegram_message("hello", bot_token=None)
                mock_post.assert_not_called()
        self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))

    def test_missing_chat_id_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_CHAT_ID": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    send_telegram_message("hello", chat_id=None)
                mock_post.assert_not_called()
        self.assertIn("TELEGRAM_CHAT_ID", str(ctx.exception))

    def test_successful_send_returns_the_api_payload(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"ok": True, "result": {"message_id": 7}}),
        ) as mock_post:
            result = send_telegram_message("hello world")

        self.assertEqual(result["ok"], True)
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage")
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_data["text"], "hello world")
        self.assertEqual(called_data["chat_id"], "12345")

    def test_explicit_credentials_override_environment(self):
        with mock.patch(
            "requests.post", return_value=FakeResponse(200, {"ok": True}),
        ) as mock_post:
            send_telegram_message(
                "hi", bot_token="explicit-token", chat_id="explicit-chat",
            )

        called_url = mock_post.call_args.args[0]
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_url, f"{TELEGRAM_API_BASE}/botexplicit-token/sendMessage")
        self.assertEqual(called_data["chat_id"], "explicit-chat")

    def test_ok_false_raises_runtime_error_with_description(self):
        payload = {"ok": False, "description": "Bad Request: chat not found"}
        with mock.patch("requests.post", return_value=FakeResponse(200, payload)):
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_message("hello")

        self.assertIn("chat not found", str(ctx.exception))

    def test_http_error_status_raises_runtime_error(self):
        with mock.patch("requests.post", return_value=FakeResponse(500, {})):
            with self.assertRaises(RuntimeError):
                send_telegram_message("hello")

    def test_never_retries_internally_on_failure(self):
        with mock.patch(
            "requests.post", return_value=FakeResponse(500, {}),
        ) as mock_post:
            with self.assertRaises(RuntimeError):
                send_telegram_message("hello")

        self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
