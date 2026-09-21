# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude
Started: 2026-09-21 17:00 Asia/Bangkok
Lease expires: 2026-09-21 21:00 Asia/Bangkok
Scope: URGENT -- found that at least 3 Shorts (aion-gentle-thailand-rice-journey-v1 "How One Grain of Rice Reaches Your Bowl", aion-illustrated-postcard-after-rain-v1 "After the Rain: Where Does the Water Go?", aion-special-octopus-chromatophores-v1 "How an Octopus Changes Color in Seconds") are already public on the channel (owner-confirmed via YouTube Studio screenshot, 17-19 Sep 2026) but have NO Studio queue memory record -- the same "lost audit entry" class of bug `reconcile_owner_confirmed_publication()` was written for, but that method had no CLI entry point. Added `reconcile-youtube-creator --episode-id --video-id --url` (main.py) so the owner can record each one without re-uploading. DO NOT run prepare-youtube-creator/quality-youtube-creator/run-youtube-creator-publish on these 3 episode ids until reconciled -- a stray "authorized-for-aion-publish" record for rice-journey was already created by mistake this session (from `prepare-youtube-creator --episode-id aion-gentle-thailand-rice-journey-v1`, run before the gap was discovered) and must be reconciled, not progressed, or it risks a duplicate upload. Also reverted an accidental `episode_number: 2` written to rice-journey's file by that same stray prepare call (git checkout, not committed). Separately noticed: Venus's own file has `episode_number: 1` but its real published title reads "EP. 002" -- a pre-existing numbering inconsistency, not caused by today's work, not yet investigated. Waiting on the owner for each episode's real video id/URL to run the new reconcile command.
Files: `main.py` (new `reconcile-youtube-creator` command), `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log entries, and this board before working. If this board still shows `in-progress` with this scope, the reconciliation is NOT done -- do not run prepare/quality/publish on the three episode ids above until it is.
