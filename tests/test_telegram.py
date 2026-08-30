"""Offline tests for tools/telegram.py.

Mocks requests.post entirely -- this suite must never make a live call
to the Telegram Bot API, per the project's rule that unit tests never
depend on a live external service.
"""

import os
import unittest
from unittest import mock

from tools.telegram import (
    TELEGRAM_API_BASE,
    send_telegram_message,
    send_telegram_message_with_buttons,
    get_telegram_updates,
    answer_telegram_callback,
)


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



class SendTelegramMessageWithButtonsTests(unittest.TestCase):

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
                send_telegram_message_with_buttons(
                    "   ", [{"text": "OK", "callback_data": "x"}],
                )
            mock_post.assert_not_called()

    def test_empty_buttons_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                send_telegram_message_with_buttons("hello", [])
            mock_post.assert_not_called()

    def test_successful_send_attaches_an_inline_keyboard(self):
        import json as _json

        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"ok": True, "result": {"message_id": 1}}),
        ) as mock_post:
            result = send_telegram_message_with_buttons(
                "อนุมัติไหมคะ",
                [
                    {"text": "อนุมัติ", "callback_data": "profile-approve:a1"},
                    {"text": "ปฏิเสธ", "callback_data": "profile-reject:a1"},
                ],
            )

        self.assertEqual(result["ok"], True)
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage")
        called_data = mock_post.call_args.kwargs["data"]
        markup = _json.loads(called_data["reply_markup"])
        buttons = markup["inline_keyboard"][0]
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0]["callback_data"], "profile-approve:a1")
        self.assertEqual(buttons[1]["callback_data"], "profile-reject:a1")

    def test_missing_bot_token_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    send_telegram_message_with_buttons(
                        "hello", [{"text": "OK", "callback_data": "x"}], bot_token=None,
                    )
                mock_post.assert_not_called()
        self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))

    def test_ok_false_raises_runtime_error(self):
        payload = {"ok": False, "description": "Bad Request: chat not found"}
        with mock.patch("requests.post", return_value=FakeResponse(200, payload)):
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_message_with_buttons(
                    "hello", [{"text": "OK", "callback_data": "x"}],
                )

        self.assertIn("chat not found", str(ctx.exception))


class GetTelegramUpdatesTests(unittest.TestCase):

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "test-bot-token"}, clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.telegram.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_returns_the_result_list(self):
        payload = {"ok": True, "result": [{"update_id": 1}, {"update_id": 2}]}
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            updates = get_telegram_updates()

        self.assertEqual(len(updates), 2)
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, f"{TELEGRAM_API_BASE}/bottest-bot-token/getUpdates")

    def test_offset_is_passed_through_as_a_param(self):
        payload = {"ok": True, "result": []}
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            get_telegram_updates(offset=43)

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["offset"], 43)

    def test_no_offset_omits_the_param(self):
        payload = {"ok": True, "result": []}
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            get_telegram_updates()

        called_params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("offset", called_params)

    def test_missing_bot_token_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            with mock.patch("requests.get") as mock_get:
                with self.assertRaises(RuntimeError):
                    get_telegram_updates(bot_token=None)
                mock_get.assert_not_called()

    def test_ok_false_raises_runtime_error(self):
        payload = {"ok": False, "description": "Unauthorized"}
        with mock.patch("requests.get", return_value=FakeResponse(200, payload)):
            with self.assertRaises(RuntimeError) as ctx:
                get_telegram_updates()

        self.assertIn("Unauthorized", str(ctx.exception))


class AnswerTelegramCallbackTests(unittest.TestCase):

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "test-bot-token"}, clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.telegram.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_empty_callback_query_id_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                answer_telegram_callback("")
            mock_post.assert_not_called()

    def test_successful_answer_returns_the_api_payload(self):
        with mock.patch(
            "requests.post", return_value=FakeResponse(200, {"ok": True}),
        ) as mock_post:
            result = answer_telegram_callback("cb1", text="อนุมัติแล้ว")

        self.assertEqual(result["ok"], True)
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, f"{TELEGRAM_API_BASE}/bottest-bot-token/answerCallbackQuery")
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_data["callback_query_id"], "cb1")
        self.assertEqual(called_data["text"], "อนุมัติแล้ว")

    def test_ok_false_raises_runtime_error(self):
        payload = {"ok": False, "description": "Bad Request: query is too old"}
        with mock.patch("requests.post", return_value=FakeResponse(200, payload)):
            with self.assertRaises(RuntimeError) as ctx:
                answer_telegram_callback("cb1")

        self.assertIn("query is too old", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
