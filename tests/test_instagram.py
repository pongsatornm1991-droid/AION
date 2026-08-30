"""Offline tests for tools/instagram.py.

Mocks requests.get/requests.post entirely -- this suite must never
make a live call to the Instagram Graph API, per the project's rule
that unit tests never depend on a live external service.
"""

import os
import unittest
from unittest import mock

from tools.instagram import (
    create_media_container,
    get_container_status,
    wait_for_container_ready,
    publish_container,
    publish_photo,
    publish_video,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"id": "container-1"}

    def json(self):
        return self._payload


class InstagramTestCase(unittest.TestCase):

    def setUp(self):
        # Isolate from whatever real .env / environment this machine
        # has -- these tests must be deterministic regardless of
        # whether real Instagram credentials happen to be configured.
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "INSTAGRAM_ACCESS_TOKEN": "test-ig-token",
                "INSTAGRAM_BUSINESS_ACCOUNT_ID": "test-ig-account-id",
            },
            clear=False,
        )
        self._env_patch.start()
        self._load_dotenv_patch = mock.patch(
            "tools.instagram.load_dotenv", return_value=None,
        )
        self._load_dotenv_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._load_dotenv_patch.stop()


class CreateMediaContainerTests(InstagramTestCase):

    def test_requires_exactly_one_of_image_url_or_video_url(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                create_media_container()
            with self.assertRaises(ValueError):
                create_media_container(
                    image_url="https://x/a.jpg", video_url="https://x/a.mp4",
                )
            mock_post.assert_not_called()

    def test_missing_access_token_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"INSTAGRAM_ACCESS_TOKEN": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    create_media_container(
                        image_url="https://x/a.jpg", access_token=None,
                    )
                mock_post.assert_not_called()
        self.assertIn("INSTAGRAM_ACCESS_TOKEN", str(ctx.exception))

    def test_missing_account_id_raises_a_clear_error(self):
        with mock.patch.dict(os.environ, {"INSTAGRAM_BUSINESS_ACCOUNT_ID": ""}):
            with mock.patch("requests.post") as mock_post:
                with self.assertRaises(RuntimeError) as ctx:
                    create_media_container(
                        image_url="https://x/a.jpg", account_id=None,
                    )
                mock_post.assert_not_called()
        self.assertIn("INSTAGRAM_BUSINESS_ACCOUNT_ID", str(ctx.exception))

    def test_photo_container_posts_image_url_not_video_fields(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "container-1"}),
        ) as mock_post:
            result = create_media_container(
                image_url="https://x/a.jpg", caption="hi",
            )
        self.assertEqual(result["id"], "container-1")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["image_url"], "https://x/a.jpg")
        self.assertNotIn("video_url", kwargs["data"])
        self.assertNotIn("media_type", kwargs["data"])

    def test_video_container_sets_media_type_video_by_default(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "container-2"}),
        ) as mock_post:
            create_media_container(video_url="https://x/a.mp4", is_reel=False)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["video_url"], "https://x/a.mp4")
        self.assertEqual(kwargs["data"]["media_type"], "VIDEO")

    def test_reel_container_sets_media_type_reels(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "container-3"}),
        ) as mock_post:
            create_media_container(video_url="https://x/a.mp4", is_reel=True)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["media_type"], "REELS")

    def test_graph_api_error_is_raised_as_runtime_error(self):
        error_payload = {
            "error": {"type": "OAuthException", "code": 190, "message": "bad token"},
        }
        with mock.patch(
            "requests.post", return_value=FakeResponse(400, error_payload),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                create_media_container(image_url="https://x/a.jpg")
        self.assertIn("bad token", str(ctx.exception))


class GetContainerStatusTests(InstagramTestCase):

    def test_empty_container_id_is_rejected_before_any_network_call(self):
        with mock.patch("requests.get") as mock_get:
            with self.assertRaises(ValueError):
                get_container_status("")
            mock_get.assert_not_called()

    def test_returns_status_code_and_status(self):
        with mock.patch(
            "requests.get",
            return_value=FakeResponse(
                200, {"status_code": "FINISHED", "status": "ok"},
            ),
        ):
            result = get_container_status("container-1")
        self.assertEqual(result["status_code"], "FINISHED")
        self.assertEqual(result["status"], "ok")


class WaitForContainerReadyTests(InstagramTestCase):

    def test_returns_immediately_once_finished(self):
        with mock.patch(
            "tools.instagram.get_container_status",
            return_value={"status_code": "FINISHED", "status": "ok"},
        ):
            with mock.patch("time.sleep") as mock_sleep:
                result = wait_for_container_ready("container-1", max_attempts=5)
        self.assertEqual(result["status_code"], "FINISHED")
        mock_sleep.assert_not_called()

    def test_polls_until_finished(self):
        statuses = [
            {"status_code": "IN_PROGRESS", "status": "..."},
            {"status_code": "IN_PROGRESS", "status": "..."},
            {"status_code": "FINISHED", "status": "ok"},
        ]
        with mock.patch(
            "tools.instagram.get_container_status", side_effect=statuses,
        ):
            with mock.patch("time.sleep") as mock_sleep:
                result = wait_for_container_ready(
                    "container-1", max_attempts=5, poll_interval=1,
                )
        self.assertEqual(result["status_code"], "FINISHED")
        self.assertEqual(mock_sleep.call_count, 2)

    def test_error_status_raises_immediately_without_exhausting_attempts(self):
        with mock.patch(
            "tools.instagram.get_container_status",
            return_value={"status_code": "ERROR", "status": "processing failed"},
        ) as mock_status:
            with mock.patch("time.sleep"):
                with self.assertRaises(RuntimeError) as ctx:
                    wait_for_container_ready("container-1", max_attempts=5)
        self.assertEqual(mock_status.call_count, 1)
        self.assertIn("processing failed", str(ctx.exception))

    def test_timeout_after_max_attempts_raises(self):
        with mock.patch(
            "tools.instagram.get_container_status",
            return_value={"status_code": "IN_PROGRESS", "status": "..."},
        ):
            with mock.patch("time.sleep"):
                with self.assertRaises(RuntimeError) as ctx:
                    wait_for_container_ready(
                        "container-1", max_attempts=3, poll_interval=1,
                    )
        self.assertIn("did not finish processing", str(ctx.exception))


class PublishContainerTests(InstagramTestCase):

    def test_empty_creation_id_is_rejected_before_any_network_call(self):
        with mock.patch("requests.post") as mock_post:
            with self.assertRaises(ValueError):
                publish_container("")
            mock_post.assert_not_called()

    def test_successful_publish_returns_the_graph_api_payload(self):
        with mock.patch(
            "requests.post",
            return_value=FakeResponse(200, {"id": "media-1"}),
        ) as mock_post:
            result = publish_container("container-1")
        self.assertEqual(result["id"], "media-1")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["creation_id"], "container-1")


class PublishPhotoTests(InstagramTestCase):

    def test_empty_image_url_is_rejected(self):
        with self.assertRaises(ValueError):
            publish_photo("")

    def test_creates_then_publishes_the_container(self):
        with mock.patch(
            "tools.instagram.create_media_container",
            return_value={"id": "container-9"},
        ) as mock_create:
            with mock.patch(
                "tools.instagram.publish_container",
                return_value={"id": "media-9"},
            ) as mock_publish:
                result = publish_photo("https://x/a.jpg", caption="hello")
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs["image_url"], "https://x/a.jpg")
        mock_publish.assert_called_once_with(
            "container-9", account_id=None, access_token=None,
        )
        self.assertEqual(result["id"], "media-9")


class PublishVideoTests(InstagramTestCase):

    def test_empty_video_url_is_rejected(self):
        with self.assertRaises(ValueError):
            publish_video("")

    def test_creates_waits_then_publishes_the_container(self):
        with mock.patch(
            "tools.instagram.create_media_container",
            return_value={"id": "container-7"},
        ) as mock_create:
            with mock.patch(
                "tools.instagram.wait_for_container_ready",
            ) as mock_wait:
                with mock.patch(
                    "tools.instagram.publish_container",
                    return_value={"id": "media-7"},
                ) as mock_publish:
                    result = publish_video("https://x/a.mp4", is_reel=True)
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs["video_url"], "https://x/a.mp4")
        self.assertTrue(mock_create.call_args.kwargs["is_reel"])
        mock_wait.assert_called_once()
        self.assertEqual(mock_wait.call_args.args[0], "container-7")
        mock_publish.assert_called_once_with(
            "container-7", account_id=None, access_token=None,
        )
        self.assertEqual(result["id"], "media-7")

    def test_processing_failure_prevents_publish(self):
        with mock.patch(
            "tools.instagram.create_media_container",
            return_value={"id": "container-8"},
        ):
            with mock.patch(
                "tools.instagram.wait_for_container_ready",
                side_effect=RuntimeError("boom"),
            ):
                with mock.patch(
                    "tools.instagram.publish_container",
                ) as mock_publish:
                    with self.assertRaises(RuntimeError):
                        publish_video("https://x/a.mp4")
        mock_publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
