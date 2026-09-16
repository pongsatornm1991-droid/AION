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

    def test_one_research_package_can_have_distinct_editorial_angles(self):
        main_short = {
            "story_package_id": "ocean-colour-01",
            "content_angle_key": "how-the-cells-work",
            "topic_key": "How an octopus changes colour",
            "source_urls": ["https://example.test/evidence"],
        }
        different_short = {
            "story_package_id": "ocean-colour-01",
            "content_angle_key": "why-it-is-not-camouflage-alone",
            "topic_key": "How an octopus changes colour",
            "source_urls": ["https://example.test/evidence"],
        }
        self.assertFalse(TopicNoveltyGate.same_topic(different_short, main_short))

    def test_one_research_package_cannot_repeat_the_same_angle(self):
        first = {"story_package_id": "ocean-colour-01", "content_angle_key": "how-the-cells-work"}
        repeat = {"story_package_id": "ocean-colour-01", "content_angle_key": "how-the-cells-work"}
        self.assertTrue(TopicNoveltyGate.same_topic(repeat, first))
