import unittest

from brain.identity_disclosure import DISCLOSURE_TH, append_identity_disclosure


class IdentityDisclosureTests(unittest.TestCase):
    def test_adds_the_exact_caption_disclosure_for_facebook_and_instagram(self):
        for platform in ("facebook", "instagram"):
            result = append_identity_disclosure("เรื่องเล่าของวันนี้", platform)
            self.assertIn(DISCLOSURE_TH, result)

    def test_is_idempotent_and_never_changes_youtube_copy(self):
        once = append_identity_disclosure("เรื่องเล่า", "instagram")
        self.assertEqual(once, append_identity_disclosure(once, "instagram"))
        self.assertEqual("เรื่องเล่า", append_identity_disclosure("เรื่องเล่า", "youtube"))
