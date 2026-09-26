"""Canonical beat names for the Creator storyboard pipeline.

Single source of truth for beat identity. Introduced 2026-09-27 after a
self-review found the same beat vocabulary independently re-declared
across multiple files: brain/story_episode_stager.py (the only place beats
are actually produced) constructs scenes with literal beat strings, and
brain/creator_scene_production.py's camera/lighting direction consumes a
subset of them by exact match. A beat renamed in one place but not the
other used to fail silently -- no exception, just a beat that quietly
stopped getting the AI narration rewrite or its camera energy.

brain/fact_first_visual_gate.py and brain/watchability_gate.py also match
beat names, but deliberately by looser substring/broader-set rules (partly
to cover long-form's many "inspection-N" filler beats without enumerating
every one). Those are pre-existing, already-tested gates; this module only
unifies the *exact-match* consumers introduced or changed in the same
session that had already concretely drifted, not every beat-matching call
site in the codebase.
"""

import re

# Short-form (13-scene) storyboard beats, in construction order.
HOOK = "hook"
QUESTION = "question"
EVIDENCE_ONE_INTRO = "evidence-one-intro"
EVIDENCE_ONE_A = "evidence-one-a"
EVIDENCE_ONE_B = "evidence-one-b"
EVIDENCE_TWO_INTRO = "evidence-two-intro"
EVIDENCE_TWO_A = "evidence-two-a"
EVIDENCE_TWO_B = "evidence-two-b"
CONNECTION = "connection"
BOUNDARY = "boundary"
TAKEAWAY = "takeaway"
INVITATION = "invitation"

# Long-form-only framing/bridge beats. Long-form's own per-source evidence
# beats are named "evidence-1", "evidence-2", ... (see
# EVIDENCE_BEAT_LONG_FORM_PATTERN below), distinct from short-form's
# "evidence-one-a"/"evidence-two-a" naming.
MAP_THE_QUESTION = "map-the-question"
FIRST_SOURCE = "first-source"
COMPARE = "compare"
UNCERTAINTY = "uncertainty"

EVIDENCE_BEAT_LONG_FORM_PATTERN = re.compile(r"^evidence-\d+$")

# Beats whose narration is a literal (or near-literal) excerpt of a source
# observation -- the ones the AI narration rewrite is allowed to retell.
EVIDENCE_LITERAL_BEATS = frozenset({
    HOOK, EVIDENCE_ONE_A, EVIDENCE_ONE_B, EVIDENCE_TWO_A, EVIDENCE_TWO_B, CONNECTION,
})

# The two beats present in both short- and long-form storyboards that
# creator_scene_production.py gives extra camera/lighting energy to.
DYNAMIC_HOOK_BEATS = frozenset({HOOK})
DYNAMIC_REVEAL_BEATS = frozenset({TAKEAWAY})


def is_evidence_literal_beat(beat):
    """True for a short-form evidence-literal beat, or any long-form evidence-N beat."""
    beat = str(beat or "")
    return beat in EVIDENCE_LITERAL_BEATS or bool(EVIDENCE_BEAT_LONG_FORM_PATTERN.match(beat))
