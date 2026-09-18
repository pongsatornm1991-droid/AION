import unittest

from brain.creator_source_integrity import CreatorSourceIntegrity


class CreatorSourceIntegrityTests(unittest.TestCase):
    def test_blocks_two_comments_as_factual_evidence(self):
        report = CreatorSourceIntegrity.assess([
            {"url": "https://news.ycombinator.com/item?id=1"},
            {"url": "https://news.ycombinator.com/item?id=2"},
        ], "How does an octopus change colour?", "Compare scientific sources.")
        self.assertFalse(report["eligible"])

    def test_accepts_two_independent_factual_sources(self):
        report = CreatorSourceIntegrity.assess([
            {"url": "https://museum.example/article"},
            {"url": "https://university.example/paper"},
        ], "How does an octopus change colour?", "Compare scientific sources.")
        self.assertTrue(report["eligible"])

    def test_allows_discussion_only_for_explicit_human_perspective(self):
        report = CreatorSourceIntegrity.assess([
            {"url": "https://news.ycombinator.com/item?id=1"},
            {"url": "https://news.ycombinator.com/item?id=2"},
        ], "What do people think about this tool?", "Collect human perspectives and conversations.")
        self.assertTrue(report["eligible"])
