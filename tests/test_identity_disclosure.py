import unittest

from brain.identity_disclosure import DISCLOSURE_TH, DISCLOSURE_YOUTUBE, append_identity_disclosure


class IdentityDisclosureTests(unittest.TestCase):
    def test_adds_the_exact_caption_disclosure_for_facebook_and_instagram(self):
        for platform in ("facebook", "instagram"):
            result = append_identity_disclosure("เรื่องเล่าของวันนี้", platform)
            self.assertIn(DISCLOSURE_TH, result)

    def test_is_idempotent_and_keeps_disclosure_in_youtube_caption_not_video(self):
        once = append_identity_disclosure("เรื่องเล่า", "instagram")
        self.assertEqual(once, append_identity_disclosure(once, "instagram"))
        youtube = append_identity_disclosure("A story", "youtube")
        self.assertIn(DISCLOSURE_YOUTUBE, youtube)
        self.assertEqual(youtube, append_identity_disclosure(youtube, "youtube"))
