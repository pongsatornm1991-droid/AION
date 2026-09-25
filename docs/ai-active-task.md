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
Handoff: Owner approved a 5-item roadmap (2026-09-25), skipped item 2
(Veo billing) as not worth it. See docs/ai-session-log.md's 2026-09-25/26
entry for full detail. Status of each:

1. DONE (commit 72fcbec) -- brain/system_integrity.py, a unified check for
   stale authorizations, motion-fallback rate, and recovery-catalogue
   depletion, wired into production_control.py + a Telegram push.
2. SKIPPED by owner request.
3. NOT STARTED -- wire real engagement data (compare-video-engagement,
   social_signals) into topic/hook decisions. Deliberately not rushed:
   the channel has 3 subscribers and low view counts right now, not
   enough signal for automated decisions to act on yet. Revisit once
   ~5-7 same-style episodes have 1-2 weeks of real view data -- check
   public/aion-production-control.json's episode list age and the
   channel directly before starting.
4. DONE (read-only review, no code) -- reviewed the real "Wait, How?"
   channel against the growth goal. Finding: the two highest-view videos
   on the channel both use the OLD, already-abandoned visual style;
   the current locked style is under-performing so far on a very small
   sample. Recommended (not yet actioned, needs owner sign-off since it
   changes public-facing titles): drop the "EP. XXX —" prefix from
   YouTube titles, since the two highest performers used direct "How
   X..." titles and the prefix buries the hook. Do NOT reopen the visual
   style decision on this little data -- revisit together with item 3
   once real per-style engagement history exists.
5. DONE (commit c428291) -- AutonomousInitiative gained a bounded,
   21-day-cooldown last-resort re-attempt for when the recovery
   catalogue has zero never-asked questions left. This is a safety net
   against total lockup, not new content -- the catalogue is still
   correctly reporting exhausted right now since nothing is old enough
   for the cooldown yet (the whole system is only weeks old).

Also from earlier the same day, still true and worth re-checking
periodically: `brain/youtube_creator_queue.py`/`creator_episode_
crosspost.py` and a couple of `tools/*.py` scripts already got
skip_invalid=True (commit 88f2220); `brain/creator_series.py`'s own
snapshot() and `brain/content_registry.py` were deliberately left
strict/untouched (see that commit message for why).
