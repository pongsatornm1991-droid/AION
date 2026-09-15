import unittest
from unittest.mock import patch

from tools import youtube


class YouTubeCommentTests(unittest.TestCase):
    def test_comment_scope_is_distinct_from_upload_scope(self):
        self.assertNotEqual(youtube.YOUTUBE_UPLOAD_SCOPE, youtube.YOUTUBE_COMMENT_SCOPE)

    @patch("tools.youtube.youtube_credentials")
    def test_reply_returns_only_safe_identifiers(self, credentials):
        class Request:
            def execute(self): return {"id": "reply-1"}
        class Comments:
            def insert(self, **_): return Request()
        class Client:
            def comments(self): return Comments()
        with patch("googleapiclient.discovery.build", return_value=Client()):
            result = youtube.reply_to_youtube_comment("parent-1", "Thank you")
        self.assertEqual({"comment_id": "reply-1", "parent_id": "parent-1"}, result)
