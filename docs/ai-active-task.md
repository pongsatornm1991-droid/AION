# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude Code
Started: 2026-09-22 17:07 UTC
Lease expires: n/a
Scope: RESOLVED. Owner authorized releasing 3 idle episodes found in the
pipeline audit. Two were blocked on Stage: invalid-cover (vertical
1080x1920 cover, long-form needs widescreen); regenerating a proper cover
via the normal AI generator failed for lack of a local OpenAI image
key/package. Owner then said to clear them without waiting on a proper
AI-generated cover, so each existing vertical cover was converted to a
valid widescreen pillarbox instead (full artwork preserved at full
height, centered over a blurred/extended version of itself as
background -- nothing cropped or distorted). Both published successfully
and independently verified genuinely public via YouTube's oEmbed API:
EP. 003 aion-longform-001-yakhchal
(https://www.youtube.com/watch?v=fy4rArLjKVU), EP. 004 aion-wonders-003
(https://www.youtube.com/watch?v=M7QlmCSmmfg). The third
(aion-auto-85365510840c-00c30e5d, octopus topic) remains withheld: strong
duplicate evidence against the already-published octopus episode (same
wonder_hook wording, one identical source URL, no visual_style ever
assigned, a status value nothing in the current codebase still writes) --
owner said they will check and handle that one manually themselves. Full
run_tests.py green throughout. See docs/ai-session-log.md's newest
2026-09-22 entry for full detail.
Handoff: read AGENTS.md and the last 10 session-log entries before
working. Still open from earlier entries: release-readiness.yml can hit a
genuine git rebase conflict on public/aion-release-readiness.json
(self-healing, not urgent); creator-scene-production.yml's
"scene-generation-unavailable" is working-as-intended, not a bug. Also
worth checking in 1-2 days: does the evidence-gathering throughput fix
(research_batch, learning-cycle.yml --limit 5) actually translate into
new episodes reaching content/creator_series/*.json.
