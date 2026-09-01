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
