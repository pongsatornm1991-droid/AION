# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude Code
Started: 2026-09-22 16:14 UTC
Lease expires: n/a
Scope: RESOLVED. Full pipeline audit found the real bottleneck: only
`run-learning-cycle` (hourly) writes qualifying research evidence, and it
only ever investigates the single top-ranked open question per run -- if
that one is blocked, the whole tick produces nothing, which is why zero
new episodes had been staged in over 2 days despite every other pipeline
stage running fine and already having its own per-run cap fixed earlier
today. Fixed with WebLearningCycle.research_batch() (brain/learning.py) +
a new `--limit` flag on `run-learning-cycle`; learning-cycle.yml now runs
`--limit 5`. Also confirmed live that the watchdog's first real dispatch
fired automatically as designed (15:52 UTC, zero human involvement), found
it mis-triggered youtube-creator.yml's strict human-operator failure check
when nothing new was ready to publish, and fixed that with a
`scheduled_recovery` dispatch input. Full run_tests.py green throughout.
See docs/ai-session-log.md's 2026-09-22 entry (top one) for full detail,
including three items explicitly flagged to the owner rather than acted on
(an unresolved content-duplicate question, two idle upload-ready
long-form episodes, three legacy unapproved visual styles).
Handoff: read AGENTS.md and the last 10 session-log entries before
working. Follow-up worth watching in 1-2 days: does the evidence-gathering
fix actually translate into new episodes reaching
content/creator_series/*.json, or does something else still throttle it
(e.g. genuine topic/novelty exhaustion rather than a per-run cap)? Also
still open from earlier entries: release-readiness.yml can hit a genuine
git rebase conflict on public/aion-release-readiness.json (self-healing,
not urgent); creator-scene-production.yml's "scene-generation-unavailable"
is working-as-intended, not a bug.
