# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude Code
Started: 2026-09-22 17:38 UTC
Lease expires: n/a
Scope: RESOLVED. Almost published a genuinely broken episode (octopus
topic) that owner had authorized -- reading its full JSON first surfaced
a `quality_incident` block (narration cuts off mid-word, confirmed by
reading the actual scenes) nothing in the codebase enforced. Retired the
episode instead (matching its already-retired -short/-long siblings) and
shipped the durable fix owner asked for: candidates() now blocks release
on quality_incident.state == "blocked" regardless of the status field.
While building the requested audit test, found a second real instance of
the same gap (aion-auto-9eebf33916e1-095c51d2-short, status
"research-returned-source-integrity" + an unenforced return_reason) and
fixed it the same way. Added tests/test_creator_series_status_hygiene.py,
which scans every real content/creator_series/*.json against a
deliberately-reviewed status allow-list so a third unenforced quarantine
status fails run_tests.py loudly instead of needing someone to notice by
hand. Full run_tests.py green throughout. See docs/ai-session-log.md's
newest 2026-09-22 entry for full detail.
Handoff: read AGENTS.md and the last 10 session-log entries before
working. Still open from earlier entries: release-readiness.yml can hit a
genuine git rebase conflict on public/aion-release-readiness.json
(self-healing, not urgent); creator-scene-production.yml's
"scene-generation-unavailable" is working-as-intended, not a bug. Also
worth checking in 1-2 days: does the evidence-gathering throughput fix
(research_batch, learning-cycle.yml --limit 5) actually translate into
new episodes reaching content/creator_series/*.json.
