"""Offline tests for tools/facebook.py.

Mocks requests.post entirely -- this suite must never make a live call
to the Facebook Graph API, per the project's rule that unit tests
never depend on a live external service.
"""

import os
import unittest
from unittest import mock

from tools.facebook import GRAPH_API_BASE, post_to_facebook_page


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


if __name__ == "__main__":
    unittest.main()
