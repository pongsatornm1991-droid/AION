"""Guards against a status value silently drifting out of sync with what
the pipeline actually enforces.

Found 2026-09-22: two episodes were quarantined by hand with a descriptive
status string (quality-blocked-story-and-audio,
research-returned-source-integrity) that nothing in the pipeline actually
read -- both were safe from automatic release only by accident, because
that exact spelling happened not to match
YouTubeCreatorQueue.READY_STATUS. One was minutes away from being
manually republished before anyone noticed the quarantine note. This test
makes any status value outside a small, deliberately reviewed allow-list
fail loudly here the next time this happens with a third spelling,
instead of depending on someone reading every file by hand.
"""

import unittest

from brain.creator_series import CreatorSeriesRegistry

# Every status value a real content/creator_series/*.json file is allowed
# to carry today, and where it comes from. Adding a new one here is a
# deliberate, reviewed decision -- if you're here because this test just
# failed on a new status, check first whether it needs its own real
# enforcement in YouTubeCreatorQueue.candidates() (see quality_incident /
# research-returned-source-integrity there for the pattern this project
# uses for a quarantine note) before simply allow-listing it away.
KNOWN_STATUSES = {
    "storyboard-ready-needs-assets",       # brain/story_episode_stager.py
    "assets-ready-for-assembly",           # brain/creator_scene_production.py
    "production-ready-assets-and-script",  # tools/assemble_creator_episode.py; YouTubeCreatorQueue.READY_STATUS
    "production-ready-script",             # an early, largely-manual stage for primary/long-form work
    "retired-do-not-publish",              # YouTubeCreatorQueue.RETIRED_STATUS -- deliberately pulled from the queue
    "research-returned-source-integrity",  # Research quarantined the draft; see its own return_reason field
}


class CreatorSeriesStatusHygieneTests(unittest.TestCase):
    def test_every_real_episode_uses_a_known_status(self):
        unknown = {
            episode["id"]: episode.get("status")
            for episode in CreatorSeriesRegistry().episodes()
            if episode.get("status") not in KNOWN_STATUSES
        }
        self.assertEqual(
            {}, unknown,
            "content/creator_series/*.json has an episode with an unrecognized "
            "status. If this is a genuine new lifecycle stage, add it to "
            "KNOWN_STATUSES deliberately. If it's a one-off quarantine note "
            "instead, give it real enforcement in "
            "YouTubeCreatorQueue.candidates() rather than just allow-listing "
            "it -- an unenforced status string is exactly what let a "
            "genuinely broken episode almost get republished on 2026-09-22.",
        )
