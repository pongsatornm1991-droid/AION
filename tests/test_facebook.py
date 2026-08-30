"""Offline tests for tools/facebook.py.

Mocks requests.post entirely -- this suite must never make a live call
to the Facebook Graph API, per the project's rule that unit tests
never depend on a live external service.
"""

import os
import unittest
from unittest import mock

from tools.facebook import (
    GRAPH_API_BASE,
    post_to_facebook_page,
    get_recent_comments,
    reply_to_facebook_comment,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"id": "123_456"}

    def json(self):
        return self._payload


class PostToFacebookPageTests(unittest.TestCase):

    def setUp(self):
        # Isolate from whatever real .env / environment this machine
        # has -- these tests must be deterministic regardless of
        # whether real Facebook credentials happen to be configured.
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "FACEBOOK_PAGE_ACCESS_TOKEN": "test-token",
                "FACEBOOK_PAGE_ID": "test-page-id",
            },
            clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.facebook.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_empty_message_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                post_to_facebook_page("   ")
            mock_post.assert_not_called()

    def test_missing_access_token_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"FACEBOOK_PAGE_ACCESS_TOKEN": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    post_to_facebook_page("hello", access_token=None)
                mock_post.assert_not_called()
        self.assertIn("FACEBOOK_PAGE_ACCESS_TOKEN", str(ctx.exception))

    def test_missing_page_id_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"FACEBOOK_PAGE_ID": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    post_to_facebook_page("hello", page_id=None)
                mock_post.assert_not_called()
        self.assertIn("FACEBOOK_PAGE_ID", str(ctx.exception))

    def test_successful_post_returns_the_graph_api_payload(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "999_888"}),
        ) as mock_post:
            result = post_to_facebook_page("hello world")

        self.assertEqual(result, {"id": "999_888"})
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, f"{GRAPH_API_BASE}/test-page-id/feed")
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_data["message"], "hello world")
        self.assertEqual(called_data["access_token"], "test-token")

    def test_explicit_credentials_override_environment(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "1"}),
        ) as mock_post:
            post_to_facebook_page(
                "hi", access_token="explicit-token", page_id="explicit-page",
            )

        called_url = mock_post.call_args.args[0]
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_url, f"{GRAPH_API_BASE}/explicit-page/feed")
        self.assertEqual(called_data["access_token"], "explicit-token")

    def test_http_error_status_raises_runtime_error_with_details(self):
        payload = {
            "error": {
                "message": "Invalid OAuth access token.",
                "type": "OAuthException",
                "code": 190,
            }
        }
        with mock.patch(
            "requests.post", return_value=FakeResponse(400, payload),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                post_to_facebook_page("hello")

        message = str(ctx.exception)
        self.assertIn("OAuthException", message)
        self.assertIn("190", message)
        self.assertIn("Invalid OAuth access token.", message)

    def test_error_key_present_even_with_200_status_still_raises(self):
        payload = {"error": {"message": "Rate limited.", "type": "X", "code": 4}}
        with mock.patch(
            "requests.post", return_value=FakeResponse(200, payload),
        ):
            with self.assertRaises(RuntimeError):
                post_to_facebook_page("hello")

    def test_never_retries_internally_on_failure(self):
        with mock.patch(
            "requests.post", return_value=FakeResponse(500, {}),
        ) as mock_post:
            with self.assertRaises(RuntimeError):
                post_to_facebook_page("hello")

        self.assertEqual(mock_post.call_count, 1)


class GetRecentCommentsTests(unittest.TestCase):

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "FACEBOOK_PAGE_ACCESS_TOKEN": "test-token",
                "FACEBOOK_PAGE_ID": "test-page-id",
            },
            clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.facebook.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_flattens_comments_from_every_post(self):
        payload = {
            "data": [
                {
                    "id": "post_1",
                    "comments": {"data": [
                        {
                            "id": "c1", "message": "hello",
                            "from": {"id": "u1", "name": "Alice"},
                            "created_time": "2026-08-30T01:00:00+0000",
                        },
                    ]},
                },
                {
                    "id": "post_2",
                    "comments": {"data": [
                        {
                            "id": "c2", "message": "hi there",
                            "from": {"id": "u2", "name": "Bob"},
                            "created_time": "2026-08-30T02:00:00+0000",
                        },
                    ]},
                },
            ]
        }
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            comments = get_recent_comments()

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]["id"], "c1")
        self.assertEqual(comments[0]["from_id"], "u1")
        self.assertEqual(comments[0]["from_name"], "Alice")
        self.assertEqual(comments[0]["post_id"], "post_1")
        self.assertEqual(comments[1]["id"], "c2")
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, f"{GRAPH_API_BASE}/test-page-id/feed")

    def test_a_post_with_no_comments_contributes_nothing(self):
        payload = {"data": [{"id": "post_1"}]}
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ):
            comments = get_recent_comments()

        self.assertEqual(comments, [])

    def test_missing_credentials_raise_before_any_network_call(self):
        with mock.patch.dict(os.environ, {"FACEBOOK_PAGE_ACCESS_TOKEN": ""}):
            with mock.patch("requests.get") as mock_get:
                with self.assertRaises(RuntimeError):
                    get_recent_comments(access_token=None)
                mock_get.assert_not_called()

    def test_graph_api_error_raises_runtime_error(self):
        payload = {
            "error": {"message": "Bad token.", "type": "OAuthException", "code": 190},
        }
        with mock.patch(
            "requests.get", return_value=FakeResponse(400, payload),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                get_recent_comments()

        self.assertIn("OAuthException", str(ctx.exception))


class ReplyToFacebookCommentTests(unittest.TestCase):

    def setUp(self):
        self._env_patch = mock.patch.dict(
            os.environ,
            {"FACEBOOK_PAGE_ACCESS_TOKEN": "test-token"},
            clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.facebook.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()

    def test_empty_message_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                reply_to_facebook_comment("c1", "   ")
            mock_post.assert_not_called()

    def test_empty_comment_id_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                reply_to_facebook_comment("", "hello")
            mock_post.assert_not_called()

    def test_successful_reply_returns_the_graph_api_payload(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "c1_reply1"}),
        ) as mock_post:
            result = reply_to_facebook_comment("c1", "ขอบคุณครับ")

        self.assertEqual(result, {"id": "c1_reply1"})
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, f"{GRAPH_API_BASE}/c1/comments")
        called_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(called_data["message"], "ขอบคุณครับ")

    def test_graph_api_error_raises_runtime_error(self):
        payload = {
            "error": {"message": "Comment not found.", "type": "GraphError", "code": 100},
        }
        with mock.patch(
            "requests.post", return_value=FakeResponse(400, payload),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                reply_to_facebook_comment("bad_id", "hi")

        self.assertIn("GraphError", str(ctx.exception))

    def test_never_retries_internally_on_failure(self):
        with mock.patch(
            "requests.post", return_value=FakeResponse(500, {}),
        ) as mock_post:
            with self.assertRaises(RuntimeError):
                reply_to_facebook_comment("c1", "hi")

        self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
