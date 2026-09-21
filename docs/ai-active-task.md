# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-21 19:05 Asia/Bangkok
Lease expires: n/a
Scope: RESOLVED -- owner asked directly to move Shorts publishing to a daily cadence. Checked real numbers first: production only ran Mon-Wed targeting 4 Shorts/week to match the old 4-day (Thu-Sun) publish cadence, and the ready buffer was only 5 episodes -- a naive publish-only change would have drained it in about a week. Asked the owner and they chose to scale production up too. Changed together: youtube-creator.yml (publish cron Thu-Sun -> daily, still 20:30 Bangkok), creator-scene-production.yml (production cron Mon-Wed -> daily; short_limit 4 -> 7), youtube-release-recovery.yml (recovery window Thu-Sun -> daily). Also fixed brain/release_readiness.py, which had its own hardcoded SHORT_DAYS={Thu,Fri,Sat,Sun} driving the 144h buffer check and a separately hardcoded target=4 -- left alone this would have kept the auto-recovery safety net only protecting 4 slots/week and silently missing shortages on the 3 newly-added days. SHORT_DAYS is now all 7 days and target derives from len(SHORT_DAYS). Updated the 3 tests that encoded the old 4-day numbers. 17 targeted tests plus the full 142-file suite (4 chunks) all pass except the pre-existing, documented memory-symlink sandbox failures (3 tests, unrelated).
Files: `.github/workflows/youtube-creator.yml`, `.github/workflows/creator-scene-production.yml`, `.github/workflows/youtube-release-recovery.yml`, `.github/workflows/release-readiness.yml` (comment only), `brain/release_readiness.py`, `tests/test_youtube_creator_schedule.py`, `tests/test_release_readiness.py`, `tests/test_release_buffer_recovery.py`, `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log entries, and this board before working. Commits `ba91974` (the cadence change) and `9725bd0` (this entry) are local-only as of this write -- confirm `git push origin main` actually ran. After it's live, watch the release buffer for the first week: it should stay near or above 7 ready short-format episodes as daily production catches up. If it keeps shrinking instead, daily production isn't actually keeping pace with daily publishing in practice (a real-world constraint like OpenAI image quota or narration-timing eligibility that wasn't checked directly this session) and the owner needs to know before a day gets skipped -- `public/aion-release-readiness.json` and the `shorts_buffer` field in it are the fastest way to check.
