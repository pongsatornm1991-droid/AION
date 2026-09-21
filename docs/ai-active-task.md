# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-21 18:43 Asia/Bangkok
Lease expires: n/a
Scope: RESOLVED -- owner asked what's next for maximum automation with no hiccups, as a genuine follow-up question. Pulled real run history from the GitHub REST API (public read for run/job metadata; log downloads need admin auth, read those via a signed-in browser tab instead) instead of guessing. Found and fixed a real bug this session's own automation-health.yml expansion introduced: its alert condition only excluded success/skipped, so routine 'cancelled' conclusions (from two watched workflows sharing a busy workflow_run-triggered concurrency group with cancel-in-progress: false -- GitHub evicts an older queued run when a newer trigger lands) paged the owner as false 'needs attention' alerts -- 17 of them in one ~10h sample. Fixed by excluding 'cancelled' too. Separately investigated AION - subject-first scene production's last 4 consecutive failures and confirmed, by reading the real CI logs and re-running the exact check against current HEAD, that all 4 predate and are fully explained by this session's earlier 2a75c27 format-aware-cover-check fix -- already resolved, no new code needed, just needs its next real run watched to confirm.
Files: `.github/workflows/automation-health.yml`, `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log entries, and this board before working. Two commits from this session are local-only as of this write (`4a5625b` cancelled-alert fix, `2975139` its session-log entry) -- confirm they were pushed with `git push origin main` before assuming they're live. Once pushed, watch the next real run of `AION - subject-first scene production` to confirm it now succeeds (last 4 runs failed, all pre-dating the 2a75c27 fix that already addresses the cause). The 28 un-migrated git-push-retry occurrences from the previous entry are still open, same handling as before: needs a human/live-CI per-file decision, not a blind pass. One unexplained single-occurrence failure (`AION - Publish public brain summary`, sha `0d1e6598`) was flagged but not investigated -- pick it up if it happens again.
