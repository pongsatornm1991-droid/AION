import os
import tempfile
import unittest
from unittest import mock

from tools.youtube import (
    YOUTUBE_UPLOAD_SCOPE, get_video_snippet, set_video_localization, update_video_description,
    upload_short, youtube_credentials,
)


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


class GetVideoSnippetTests(unittest.TestCase):
    ENV = {"YOUTUBE_REFRESH_TOKEN": "t", "YOUTUBE_CLIENT_ID": "c", "YOUTUBE_CLIENT_SECRET": "s"}

    def test_rejects_a_blank_video_id_before_contacting_youtube(self):
        with self.assertRaises(ValueError):
            get_video_snippet("")

    def test_returns_the_live_title_and_description(self):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {
            "items": [{"snippet": {"title": "Real title", "description": "Real description"}}],
        }
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            result = get_video_snippet("abc")
        self.assertEqual({"title": "Real title", "description": "Real description"}, result)

    def test_raises_when_the_video_id_does_not_resolve(self):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            with self.assertRaises(RuntimeError):
                get_video_snippet("missing")


class UpdateVideoDescriptionTests(unittest.TestCase):
    ENV = {"YOUTUBE_REFRESH_TOKEN": "t", "YOUTUBE_CLIENT_ID": "c", "YOUTUBE_CLIENT_SECRET": "s"}

    def test_rejects_a_blank_video_id_before_contacting_youtube(self):
        with self.assertRaises(ValueError):
            update_video_description("", "new description")

    def test_replaces_only_the_description_preserving_the_rest_of_the_snippet(self):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {
            "items": [{"snippet": {"title": "Real title", "description": "Old", "categoryId": "28"}}],
        }
        fake_youtube.videos.return_value.update.return_value.execute.return_value = {
            "snippet": {"description": "New description"},
        }
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            result = update_video_description("abc", "New description")
        body = fake_youtube.videos.return_value.update.call_args.kwargs["body"]
        self.assertEqual("Real title", body["snippet"]["title"])
        self.assertEqual("28", body["snippet"]["categoryId"])
        self.assertEqual("New description", body["snippet"]["description"])
        self.assertEqual("New description", result["description"])

    def test_raises_when_the_video_id_does_not_resolve(self):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            with self.assertRaises(RuntimeError):
                update_video_description("missing", "New description")


class SetVideoLocalizationTests(unittest.TestCase):
    ENV = {"YOUTUBE_REFRESH_TOKEN": "t", "YOUTUBE_CLIENT_ID": "c", "YOUTUBE_CLIENT_SECRET": "s"}

    def _fake_youtube(self, existing_snippet, existing_localizations=None):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {
            "items": [{"snippet": existing_snippet, "localizations": existing_localizations or {}}],
        }
        fake_youtube.videos.return_value.update.return_value.execute.return_value = {
            "localizations": {**(existing_localizations or {})},
        }
        return fake_youtube

    def test_rejects_a_blank_video_id_or_language_code_before_contacting_youtube(self):
        with self.assertRaises(ValueError):
            set_video_localization("", "th", "title", "desc")
        with self.assertRaises(ValueError):
            set_video_localization("abc", "", "title", "desc")

    def test_adds_a_defaultLanguage_when_the_video_has_none_so_the_write_is_not_rejected(self):
        fake_youtube = self._fake_youtube({"title": "Original", "description": "Original desc"})
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            set_video_localization("abc", "th", "หัวข้อ", "คำอธิบาย")
        body = fake_youtube.videos.return_value.update.call_args.kwargs["body"]
        self.assertEqual("en", body["snippet"]["defaultLanguage"])
        self.assertEqual({"title": "หัวข้อ", "description": "คำอธิบาย"}, body["localizations"]["th"])

    def test_preserves_the_existing_snippet_and_other_languages_instead_of_overwriting_them(self):
        fake_youtube = self._fake_youtube(
            {"title": "Original", "description": "Original desc", "defaultLanguage": "en", "categoryId": "28"},
            existing_localizations={"es": {"title": "Original ES", "description": "Desc ES"}},
        )
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            set_video_localization("abc", "th", "หัวข้อ", "คำอธิบาย")
        body = fake_youtube.videos.return_value.update.call_args.kwargs["body"]
        self.assertEqual("28", body["snippet"]["categoryId"])
        self.assertEqual("Original ES", body["localizations"]["es"]["title"])
        self.assertEqual("หัวข้อ", body["localizations"]["th"]["title"])

    def test_raises_when_the_video_id_does_not_resolve_to_a_real_upload(self):
        fake_youtube = mock.MagicMock()
        fake_youtube.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch("googleapiclient.discovery.build", return_value=fake_youtube):
            with self.assertRaises(RuntimeError):
                set_video_localization("missing", "th", "title", "desc")
