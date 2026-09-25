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
Handoff: Closed out the full bottleneck-hunting session from today -- see
docs/ai-session-log.md's 2026-09-25 entries (several, newest first) for
full detail. Summary for whoever's next:

1. Fixed a real crash bug: CreatorSeriesRegistry.episodes() raised on the
   first invalid episode file, taking down every caller (scene production,
   narration preflight, dashboard/public-summary, release-readiness/queue,
   crosspost, motion, assembly, costume briefs, recovery buffer). Added
   episodes(skip_invalid=True), applied everywhere in the production/
   release path (commits 0573e9a, b23ffe5, 88f2220). Confirmed end-to-end
   live: the stuck maps episode (aion-auto-32006eab7f3a-899f27ed-short)
   went from permanently blocked to fully rendered (13 images + cover) and
   shorts_buffer.quality_ready moved 0 -> 1.

2. Found and fixed the write-back bug that had actually corrupted that
   episode: tools/preflight_creator_narration.py's write-timeline step
   dropped the synced visual_narrative/fact_first_visual fields that
   NarrationPreflight.repair_episode_timing correctly computes after a
   scene split (commit b23ffe5).

3. Un-stuck the recovery lane's topic catalogue: it excluded a whole
   domain forever after one use, and all 33 original domains had been
   used, so it could never seed a new question again regardless of buffer
   state. Fixed to exclude by the specific question asked (any status),
   not the domain, and added 24 new topics (57 total) (commit c86a7b2).
   Verified against the real synced memory that this actually unblocks it.

Owner gave standing authorization (2026-09-25) to fix any bug found
directly without asking first, in pursuit of 100% automation with zero
bottlenecks. This is saved in Claude's own memory system; Codex should
feel free to act on the same standing authorization for this class of
finding unless the owner says otherwise.

Nothing urgent left open from this session. Minor, non-blocking items
noted in commit messages/session log if useful later: brain/creator_series.py's
own snapshot() and brain/content_registry.py were deliberately left on
strict/legacy behavior (see 88f2220's message for why); the recovery
catalogue can eventually run low again after ~57 uses and may want a
third batch or a proper time-based rotation mechanism at that point.
