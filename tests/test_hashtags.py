"""Offline tests for brain/hashtags.py -- the static, curated
multilingual hashtag block appended to AION's own posts (2026-08-31).
Pure string logic, no network/AI-provider/memory access."""

import unittest

from brain.hashtags import HASHTAG_SETS, append_hashtags, build_hashtag_block


class BuildHashtagBlockTests(unittest.TestCase):

    def test_returns_a_single_space_joined_line(self):
        block = build_hashtag_block()

        self.assertIsInstance(block, str)
        self.assertNotIn("\n", block)
        for tag in block.split(" "):
            self.assertTrue(tag.startswith("#"))

    def test_includes_at_least_one_tag_per_configured_language(self):
        block = build_hashtag_block()

        for lang, tags in HASHTAG_SETS.items():
            self.assertTrue(
                any(tag in block for tag in tags),
                f"no tag from {lang!r} found in the hashtag block",
            )

    def test_thai_and_english_tags_are_present(self):
        # The two languages every other test in this codebase assumes
        # AION's own drafted text is written in -- a regression here
        # would mean the home-language/primary-reach tags silently
        # dropped out of the block.
        block = build_hashtag_block()

        self.assertIn("#เอไอ", block)
        self.assertIn("#AI", block)

    def test_duplicate_tags_across_languages_are_not_repeated(self):
        # Portuguese and Spanish currently share identical tag text
        # ("#IA", "#InteligenciaArtificial") -- the block must not
        # contain either tag twice.
        block = build_hashtag_block()
        tags = block.split(" ")

        self.assertEqual(len(tags), len(set(tags)))

    def test_is_deterministic(self):
        self.assertEqual(build_hashtag_block(), build_hashtag_block())


class AppendHashtagsTests(unittest.TestCase):

    def test_appends_the_block_after_a_blank_line(self):
        result = append_hashtags("สวัสดีครับ")

        self.assertTrue(result.startswith("สวัสดีครับ\n\n"))
        self.assertIn("#AI", result)

    def test_original_text_is_preserved_verbatim_up_to_the_separator(self):
        text = "วันนี้ AION กำลังสนใจเรื่องความจำของตัวเองอยู่ครับ"
        result = append_hashtags(text)

        self.assertEqual(result.split("\n\n")[0], text)

    def test_empty_text_is_returned_unchanged(self):
        self.assertEqual(append_hashtags(""), "")
        self.assertIsNone(append_hashtags(None))


if __name__ == "__main__":
    unittest.main()
