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
Handoff: URGENT, needs the owner directly (not code-fixable by either of
us) -- see docs/ai-session-log.md's 2026-09-25 "URGENT" entry, commits
5c96916 / f3b2c05. YouTube's YOUTUBE_REFRESH_TOKEN is expired/revoked
(`invalid_grant`), confirmed from real Actions logs on both tonight's run
and 2026-09-22's -- no automatic YouTube upload has succeeded in at least
5 days. The Shorts buffer being fixed (see the two entries below this one)
does NOT matter until this is resolved: episodes will keep authorizing
successfully and then failing to actually upload.

Fix needs the owner's own Google account (OAuth consent), so neither Codex
nor Claude can do it directly: run `python tools/youtube_authorize.py
--client-secrets <path-to-downloaded-client-secret.json>` locally, then
put the printed refresh token into the `YOUTUBE_REFRESH_TOKEN` GitHub
Actions secret. If Codex or Claude picks this up next and the owner is
present, offer to walk through it step by step rather than assuming it's
already been done -- check for a fresh `Stage: published` in the next
youtube-creator.yml run before assuming it's fixed.

Also fixed as part of the same investigation: the CI job used to report
green even when this exact fault happened on a scheduled or self-healing
recovery run (only an explicit manual request used to fail loudly) --
that's why this went unnoticed for days. Now `Stage: upload-failed` always
fails the run. This means: once the token is fixed, if publishing still
fails for some other reason, it WILL show up as a failed workflow run --
that's the fix working as intended, not a new problem.
