"""Tests for brain.manual_publish -- the manual "upload my own video"
pipeline (YouTube upload, then Facebook + Instagram link posts).

Mirrors this project's established stub-and-patch convention (see
tests/test_social.py, tests/test_providers.py): no real network calls,
everything goes through unittest.mock.patch on the three tools.* entry
points manual_publish.py imports by name.
"""

import unittest
from unittest.mock import patch

from brain.manual_publish import (
    DEFAULT_INSTAGRAM_ANNOUNCE_IMAGE,
    publish_local_video_everywhere,
)


class PublishLocalVideoEverywhereTests(unittest.TestCase):
    def _youtube_result(self):
        return {
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "privacy_status": "public",
        }

    @patch("brain.manual_publish.publish_photo")
    @patch("brain.manual_publish.post_to_facebook_page")
    @patch("brain.manual_publish.upload_short")
    def test_happy_path_posts_to_all_three(self, mock_upload, mock_fb, mock_ig):
        mock_upload.return_value = self._youtube_result()
        mock_fb.return_value = {"id": "fb-1"}
        mock_ig.return_value = {"id": "ig-1"}

        report = publish_local_video_everywhere(
            "/tmp/video.mp4", "My Title", caption="ดูคลิปนี้สิ",
        )

        self.assertEqual(report["stage"], "done")
        self.assertEqual(report["youtube"]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(report["facebook"], {"status": "ok", "id": "fb-1"})
        self.assertEqual(report["instagram"], {"status": "ok", "id": "ig-1"})

        # The YouTube link must actually be in both posted messages.
        fb_message = mock_fb.call_args.args[0]
        self.assertIn("https://www.youtube.com/watch?v=abc123", fb_message)
        ig_kwargs = mock_ig.call_args.kwargs
        self.assertIn("https://www.youtube.com/watch?v=abc123", ig_kwargs["caption"])
        self.assertEqual(ig_kwargs["image_url"], DEFAULT_INSTAGRAM_ANNOUNCE_IMAGE)

    @patch("brain.manual_publish.upload_short")
    def test_youtube_failure_raises_and_never_posts(self, mock_upload):
        mock_upload.side_effect = RuntimeError("quota exceeded")

        with patch("brain.manual_publish.post_to_facebook_page") as mock_fb, \
             patch("brain.manual_publish.publish_photo") as mock_ig:
            with self.assertRaises(RuntimeError):
                publish_local_video_everywhere("/tmp/video.mp4", "My Title")
            mock_fb.assert_not_called()
            mock_ig.assert_not_called()

    @patch("brain.manual_publish.publish_photo")
    @patch("brain.manual_publish.post_to_facebook_page")
    @patch("brain.manual_publish.upload_short")
    def test_facebook_failure_does_not_block_instagram(self, mock_upload, mock_fb, mock_ig):
        mock_upload.return_value = self._youtube_result()
        mock_fb.side_effect = RuntimeError("Facebook Graph API error")
        mock_ig.return_value = {"id": "ig-1"}

        report = publish_local_video_everywhere("/tmp/video.mp4", "My Title")

        self.assertEqual(report["facebook"]["status"], "failed")
        self.assertIn("Facebook Graph API error", report["facebook"]["error"])
        self.assertEqual(report["instagram"], {"status": "ok", "id": "ig-1"})
        self.assertEqual(report["stage"], "done")

    @patch("brain.manual_publish.publish_photo")
    @patch("brain.manual_publish.post_to_facebook_page")
    @patch("brain.manual_publish.upload_short")
    def test_skip_flags_are_honored(self, mock_upload, mock_fb, mock_ig):
        mock_upload.return_value = self._youtube_result()

        report = publish_local_video_everywhere(
            "/tmp/video.mp4", "My Title", skip_facebook=True, skip_instagram=True,
        )

        mock_fb.assert_not_called()
        mock_ig.assert_not_called()
        self.assertEqual(report["facebook"], {"status": "skipped"})
        self.assertEqual(report["instagram"], {"status": "skipped"})

    @patch("brain.manual_publish.publish_photo")
    @patch("brain.manual_publish.post_to_facebook_page")
    @patch("brain.manual_publish.upload_short")
    def test_custom_instagram_image_overrides_default(self, mock_upload, mock_fb, mock_ig):
        mock_upload.return_value = self._youtube_result()
        mock_ig.return_value = {"id": "ig-1"}

        publish_local_video_everywhere(
            "/tmp/video.mp4", "My Title",
            instagram_image_url="https://example.com/custom.png",
        )

        self.assertEqual(mock_ig.call_args.kwargs["image_url"], "https://example.com/custom.png")


if __name__ == "__main__":
    unittest.main()
