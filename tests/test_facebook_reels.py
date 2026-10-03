import os
import unittest
from unittest import mock

from tools.facebook import publish_reel_to_facebook


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FacebookReelTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "FACEBOOK_PAGE_ACCESS_TOKEN": "page-token",
            "FACEBOOK_PAGE_ID": "page-id",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_uploads_then_publishes_a_page_reel(self):
        source = mock.Mock(status_code=200, headers={"content-length": "3"})
        source.iter_content.return_value = [b"mp4"]
        responses = [
            _Response({"video_id": "video-1", "upload_url": "https://upload.example/video-1"}),
            _Response({"success": True}),
            _Response({"success": True, "id": "video-1"}),
        ]
        with mock.patch("requests.get", return_value=source) as get:
            with mock.patch("requests.post", side_effect=responses) as post:
                result = publish_reel_to_facebook("https://cdn.example/reel.mp4", "AION begins")

        self.assertEqual(result["id"], "video-1")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(get.call_args.args[0], "https://cdn.example/reel.mp4")
        self.assertEqual(post.call_args_list[0].kwargs["data"]["upload_phase"], "start")
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["Content-Type"], "application/octet-stream")
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["X-Entity-Length"], "3")
        self.assertEqual(post.call_args_list[2].kwargs["data"]["video_state"], "PUBLISHED")

    def test_uploads_a_local_file_without_downloading_anything(self):
        # The Thai-audio Reels are rendered inside the workflow run and never
        # committed, so they have no public URL to download from.
        import tempfile
        responses = [
            _Response({"video_id": "video-2", "upload_url": "https://upload.example/video-2"}),
            _Response({"success": True}),
            _Response({"success": True, "id": "video-2"}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "thai.mp4")
            with open(path, "wb") as handle:
                handle.write(b"thai-mp4")
            with mock.patch("requests.get") as get, mock.patch("requests.post", side_effect=responses) as post:
                result = publish_reel_to_facebook(path, "ภาษาไทย")
        self.assertEqual("video-2", result["id"])
        get.assert_not_called()
        self.assertEqual(b"thai-mp4", post.call_args_list[1].kwargs["data"])
        self.assertEqual("8", post.call_args_list[1].kwargs["headers"]["X-Entity-Length"])

    def test_rejects_empty_video_url_before_network_calls(self):
        with mock.patch("requests.post") as post:
            with self.assertRaises(ValueError):
                publish_reel_to_facebook("")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
