import os
import tempfile
import unittest
from unittest import mock

from tools.youtube import YOUTUBE_UPLOAD_SCOPE, upload_short, youtube_credentials


class YouTubeUploadTests(unittest.TestCase):
    def test_credentials_require_all_secret_environment_values(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "YOUTUBE_REFRESH_TOKEN"):
                youtube_credentials()

    def test_upload_rejects_missing_file_before_contacting_youtube(self):
        with self.assertRaises(FileNotFoundError):
            upload_short("does-not-exist.mp4", "AION", "A thought")

    def test_upload_rejects_non_video_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as handle:
            with self.assertRaises(ValueError):
                upload_short(handle.name, "AION", "A thought")

    def test_scope_is_upload_only(self):
        self.assertEqual(YOUTUBE_UPLOAD_SCOPE, "https://www.googleapis.com/auth/youtube.upload")

    def test_tags_are_included_in_the_upload_request_when_supplied(self):
        # Regression for 2026-09-26: every prior real upload sent no tags at
        # all -- this locks in that the field actually reaches the request
        # body once the caller supplies one.
        with tempfile.NamedTemporaryFile(suffix=".mp4") as handle:
            handle.write(b"video-bytes")
            handle.flush()
            fake_request = mock.MagicMock()
            fake_request.next_chunk.return_value = (None, {"id": "abc", "status": {"privacyStatus": "public"}})
            fake_youtube = mock.MagicMock()
            fake_youtube.videos.return_value.insert.return_value = fake_request
            with mock.patch.dict(os.environ, {
                "YOUTUBE_REFRESH_TOKEN": "t", "YOUTUBE_CLIENT_ID": "c", "YOUTUBE_CLIENT_SECRET": "s",
            }, clear=False), \
                 mock.patch("googleapiclient.discovery.build", return_value=fake_youtube), \
                 mock.patch("googleapiclient.http.MediaFileUpload"):
                upload_short(handle.name, "A useful question", "desc", privacy_status="public",
                             tags=["maps", "cartography", "AION", "Shorts"])
            body = fake_youtube.videos.return_value.insert.call_args.kwargs["body"]
            self.assertEqual(["maps", "cartography", "AION", "Shorts"], body["snippet"]["tags"])

    def test_tags_are_trimmed_to_the_500_character_budget_not_rejected_outright(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as handle:
            handle.write(b"video-bytes")
            handle.flush()
            fake_request = mock.MagicMock()
            fake_request.next_chunk.return_value = (None, {"id": "abc", "status": {"privacyStatus": "public"}})
            fake_youtube = mock.MagicMock()
            fake_youtube.videos.return_value.insert.return_value = fake_request
            long_tags = [f"keyword-{i}" * 10 for i in range(20)]  # each ~90 chars
            with mock.patch.dict(os.environ, {
                "YOUTUBE_REFRESH_TOKEN": "t", "YOUTUBE_CLIENT_ID": "c", "YOUTUBE_CLIENT_SECRET": "s",
            }, clear=False), \
                 mock.patch("googleapiclient.discovery.build", return_value=fake_youtube), \
                 mock.patch("googleapiclient.http.MediaFileUpload"):
                upload_short(handle.name, "Title", "desc", privacy_status="public", tags=long_tags)
            body = fake_youtube.videos.return_value.insert.call_args.kwargs["body"]
            kept = body["snippet"]["tags"]
            self.assertLess(len(kept), len(long_tags))
            self.assertLessEqual(sum(len(t) + 1 for t in kept), 500)
