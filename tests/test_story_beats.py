import unittest

from brain import creator_scene_production, story_beats


class IsEvidenceLiteralBeatTests(unittest.TestCase):
    def test_flags_every_short_form_evidence_literal_beat(self):
        for beat in (
            story_beats.HOOK, story_beats.EVIDENCE_ONE_A, story_beats.EVIDENCE_ONE_B,
            story_beats.EVIDENCE_TWO_A, story_beats.EVIDENCE_TWO_B, story_beats.CONNECTION,
        ):
            self.assertTrue(story_beats.is_evidence_literal_beat(beat), beat)

    def test_flags_any_long_form_evidence_n_beat(self):
        self.assertTrue(story_beats.is_evidence_literal_beat("evidence-1"))
        self.assertTrue(story_beats.is_evidence_literal_beat("evidence-42"))

    def test_does_not_flag_a_hand_authored_template_beat(self):
        for beat in (
            story_beats.QUESTION, story_beats.EVIDENCE_ONE_INTRO, story_beats.EVIDENCE_TWO_INTRO,
            story_beats.BOUNDARY, story_beats.INVITATION, story_beats.MAP_THE_QUESTION,
            story_beats.FIRST_SOURCE, story_beats.COMPARE, story_beats.UNCERTAINTY,
        ):
            self.assertFalse(story_beats.is_evidence_literal_beat(beat), beat)

    def test_does_not_flag_an_unknown_or_missing_beat(self):
        self.assertFalse(story_beats.is_evidence_literal_beat("some-other-beat"))
        self.assertFalse(story_beats.is_evidence_literal_beat(None))
        self.assertFalse(story_beats.is_evidence_literal_beat(""))


class CrossFileBeatConsistencyTests(unittest.TestCase):
    """Regression for the exact 2026-09-27 self-review finding this module
    fixes: creator_scene_production.py's dynamic-composition beats and
    story_episode_stager.py's AI-rewrite-eligible beats used to be two
    independently hand-typed string sets with no shared source of truth. A
    rename in one used to silently desync the other with no failing test
    anywhere. Both now import from brain.story_beats, so this test would
    fail loudly the moment that stops being true."""

    def test_creator_scene_production_imports_the_same_constants(self):
        self.assertIs(creator_scene_production.DYNAMIC_HOOK_BEATS, story_beats.DYNAMIC_HOOK_BEATS)
        self.assertIs(creator_scene_production.DYNAMIC_REVEAL_BEATS, story_beats.DYNAMIC_REVEAL_BEATS)


if __name__ == "__main__":
    unittest.main()
