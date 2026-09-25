# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: none
Started: n/a
Lease expires: n/a
Scope: None.
Handoff: Found and fixed the REAL reason the Shorts buffer stayed at 0/7 even
after yesterday's registry fix (0573e9a) -- see docs/ai-session-log.md's
2026-09-25 "Found the real reason..." entry, commit b23ffe5. Short version:
1. Two more callers (tools/preflight_creator_narration.py,
   brain/studio_pipeline.py) still crashed on a single invalid episode --
   same fix as before, skip_invalid=True, both now covered.
2. The actual root cause of THAT episode being invalid: NarrationPreflight.
   repair_episode_timing correctly syncs visual_narrative.scene_progression
   and fact_first_visual.scene_roles after a scene split, but
   preflight_creator_narration.py's write-back was silently dropping both
   fields when persisting to disk -- a real, previously-undiscovered bug in
   this morning's "sync metadata after repair" fix. One episode
   (aion-auto-32006eab7f3a-899f27ed-short) got permanently deadlocked by it.
   Fixed the write-back; manually repaired that episode's on-disk metadata
   so it's producible again right now.
3. `CreatorSeriesRegistry().episodes()` now loads all 19 real episodes
   without raising, and CreatorSceneProduction picks the maps episode again.
   Full test suite green (this also fixed 5 tests that were ERRORing
   because the real content directory genuinely had corrupted data --
   test_creator_series.py x3, test_creator_series_status_hygiene.py,
   test_dashboard.py -- not because those tests were wrong).

Still open, not fixed this round (flagged, not urgent -- no live workflow is
currently failing because of these):
- brain/youtube_creator_queue.py:120 and brain/creator_episode_crosspost.py:35
  still call .episodes() without skip_invalid=True. Same latent crash risk
  if a future episode goes invalid.
- brain/release_readiness.py's snapshot() catches
  (OSError, ValueError, TypeError) around YouTubeCreatorQueue(...).candidates()
  and falls back to an empty list -- this doesn't crash, but it silently
  hides EVERY candidate (not just the broken one) whenever any single
  episode is invalid. Worth switching to skip_invalid=True instead of the
  blanket except; may have been under-reporting the buffer.

If a new episode gets stuck the same way again, check whether it was
recently split by NarrationPreflight.repair_episode_timing and whether its
visual_narrative/fact_first_visual scene counts match its actual scenes
count before assuming it's a new bug.
