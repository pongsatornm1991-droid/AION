# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-21 09:30 Asia/Bangkok
Lease expires: n/a
Scope: Venus flytrap verified public (see prior entry). Added a style lock so a clip can only enter the release queue with an explicit `visual_style.approved: true` -- closes the gap that let the urgent-priority old-style rainbow clip win an automatic slot. Opt-in flag, checked in YouTubeCreatorQueue.candidates(); backfilled onto the current in-flight ready episodes (Thailand rice journey, postcard-after-rain, yakhchal, octopus, wonders-003, venus) since they were already legitimately queued; deliberately left the rainbow episode's style unapproved. story_episode_stager.py now stamps approved:true on new AION Wonders episodes automatically. See docs/ai-session-log.md 2026-09-21 entry for the full story.
Files: `brain/youtube_creator_queue.py`, `brain/story_episode_stager.py`, `tests/test_youtube_creator_queue.py`, `tests/test_release_readiness.py`, `tests/test_release_buffer_recovery.py`, `content/creator_series/*.json` (6 files, approved flag only), `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log entries, and this board before working. If a future in-flight episode is blocked by "visual-style-not-approved-for-release", that is by design -- it needs an explicit `visual_style.approved: true` from whoever signs off on its look, not a code workaround.
