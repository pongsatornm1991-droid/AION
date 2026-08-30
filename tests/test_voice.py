"""Offline tests for SocialContentGenerator.unified_style_notes() --
the shared voice every drafting context (posts, comment replies,
profile bios, web-learning answers) now draws its recent
style-review lessons from (2026-08-30), so a correction learned in
one context reaches every other context instead of staying isolated.
"""

import shutil
import tempfile
import time
import unittest

from brain.memory import MemoryEngine
from brain.social import SocialContentGenerator


class _MemoryOnly:
    """Minimal duck-typed stand-in exposing just `.memory`, enough to
    call any of the four modules' recent_style_notes(self, ...) as an
    unbound method without constructing their full (generator,
    lifecycle, curiosity, ...) dependency graphs."""

    def __init__(self, memory):
        self.memory = memory


class UnifiedStyleNotesTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_memory_returns_no_notes(self):
        self.assertEqual(
            SocialContentGenerator.unified_style_notes(self.memory), [],
        )

    def test_pulls_lessons_from_every_drafting_context(self):
        self.memory.remember(
            category="lessons",
            content="Blocked a social-post draft (robotic_style): post note",
            memory_type="lesson", source="social-style-review", importance=3,
        )
        self.memory.remember(
            category="comment_replies",
            content="Blocked a reply draft (robotic_style): reply note",
            memory_type="lesson", source="comment-style-review", importance=3,
        )
        self.memory.remember(
            category="lessons",
            content="Blocked a bio draft (robotic_style): bio note",
            memory_type="lesson", source="profile-style-review", importance=3,
        )
        self.memory.remember(
            category="lessons",
            content="Blocked a learning-answer draft (robotic_style): learning note",
            memory_type="lesson", source="learning-style-review", importance=3,
        )

        notes = SocialContentGenerator.unified_style_notes(self.memory)

        self.assertEqual(len(notes), 4)
        self.assertTrue(any("post note" in n for n in notes))
        self.assertTrue(any("reply note" in n for n in notes))
        self.assertTrue(any("bio note" in n for n in notes))
        self.assertTrue(any("learning note" in n for n in notes))

    def test_ignores_unrelated_lessons_and_records(self):
        self.memory.remember(
            category="lessons",
            content="Blocked a social-post draft (claim_safety): unrelated",
            memory_type="lesson", source="social-safety-gate", importance=3,
        )
        self.memory.remember(
            category="comment_replies",
            content="Replied to a real comment successfully",
            memory_type="observation", source="comment-reply-handled",
            importance=2,
        )

        self.assertEqual(
            SocialContentGenerator.unified_style_notes(self.memory), [],
        )

    def test_most_recent_first_across_contexts_and_respects_limit(self):
        self.memory.remember(
            category="lessons", content="oldest: social note",
            memory_type="lesson", source="social-style-review", importance=3,
        )
        time.sleep(1.1)
        self.memory.remember(
            category="comment_replies", content="middle: reply note",
            memory_type="lesson", source="comment-style-review", importance=3,
        )
        time.sleep(1.1)
        self.memory.remember(
            category="lessons", content="newest: bio note",
            memory_type="lesson", source="profile-style-review", importance=3,
        )

        notes = SocialContentGenerator.unified_style_notes(self.memory, limit=2)

        self.assertEqual(len(notes), 2)
        self.assertIn("newest: bio note", notes[0])
        self.assertIn("middle: reply note", notes[1])

    def test_each_modules_recent_style_notes_delegates_to_the_shared_function(self):
        from brain.comment_reply import CommentAutoReplyCycle
        from brain.learning import WebLearningCycle
        from brain.profile_change import ProfileChangeCycle

        self.memory.remember(
            category="lessons", content="cross-context social note",
            memory_type="lesson", source="social-style-review", importance=3,
        )

        expected = SocialContentGenerator.unified_style_notes(self.memory)
        self.assertEqual(len(expected), 1)

        stub = _MemoryOnly(self.memory)
        self.assertEqual(
            CommentAutoReplyCycle.recent_style_notes(stub), expected,
        )
        self.assertEqual(
            WebLearningCycle.recent_style_notes(stub), expected,
        )
        self.assertEqual(
            ProfileChangeCycle.recent_style_notes(stub), expected,
        )


if __name__ == "__main__":
    unittest.main()
