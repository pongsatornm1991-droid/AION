import unittest

from brain.topic_novelty import TopicNoveltyGate


class TopicNoveltyGateTests(unittest.TestCase):
    def test_common_helper_words_do_not_make_unrelated_topics_duplicates(self):
        candidate = {"topic_key": "How can an octopus change color so quickly?"}
        earlier = {"caption": "AION reflection: small signals can change a path."}
        self.assertFalse(TopicNoveltyGate.same_topic(candidate, earlier))

    def test_specific_subject_still_blocks_a_repeat(self):
        self.assertTrue(TopicNoveltyGate.same_topic(
            {"topic_key": "How did Persian yakhchal structures store ice?"},
            {"topic_key": "Persian yakhchal ice storage"},
        ))
