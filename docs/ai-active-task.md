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
Handoff: Fixed two live issues found by an owner-requested bottleneck audit --
see docs/ai-session-log.md's 2026-09-25 Claude Code entry for full detail,
commit 0573e9a. Summary for whoever's next:
1. `main` was red for 5 commits (stale enabled-source list in
   tests/test_curiosity_constitution.py, missing `openalex`) -- fixed, full
   suite green again.
2. CreatorSeriesRegistry.episodes() (brain/creator_series.py) used to raise
   on the FIRST invalid episode file and crash the whole call for every
   caller -- this is why creator-scene-production.yml failed 4 runs in a row
   while the Shorts buffer sat at 0/7: one broken storyboard blocked every
   other ready episode too, not just its own slot. Added
   episodes(skip_invalid=True); CreatorSceneProduction._episode() now uses
   it and reports excluded episodes in report["invalid_episodes"] instead of
   crashing. Default (skip_invalid=False) is unchanged, so
   tests/test_creator_series.py's raise-on-bad-content gate still works.
If the Shorts buffer is still not recovering a day or two after this lands,
that's a *different* problem (e.g. evidence/story-brief throughput) --
check public/aion-production-control.json's `recovery`/`evidence_reserve`
sections and `report["invalid_episodes"]` from the next
creator-scene-production.yml run before assuming this fix didn't work.
