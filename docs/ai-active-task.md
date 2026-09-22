# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 17:38 UTC
Lease expires: 2026-09-22 19:38 UTC
Scope: Almost published a genuinely broken episode by mistake. Reading the
octopus episode's full JSON before publishing (owner had authorized it)
surfaced a `quality_incident` block never shown before: {"state":
"blocked", "reasons": ["narration-ends-before-final-scene",
"generic-template-story-does-not-explain-topic"], "action": "Do not
reuse..."} -- verified for real by reading the actual scene narration,
which does cut off mid-word twice. Owner said retire it instead, and
asked for a durable fix so this can't slip through again. Root cause:
`quality_incident` is a purely documentary field nobody's code reads --
grepped the whole repo, it appears in exactly this one JSON file and
nowhere else. The only reason this episode was ever safe was that its
status string ("quality-blocked-story-and-audio") happens not to match
YouTubeCreatorQueue.READY_STATUS -- an accident of spelling, not an
enforced gate. Its own -short/-long sibling files were already correctly
set to retired-do-not-publish; only this un-suffixed file (the one
candidates() actually reads, since it matches the internal id field) was
left in the non-standard, unenforced state. Fixing: (1) set this
episode's own status to retired-do-not-publish to match its siblings;
(2) add a real, enforced check in YouTubeCreatorQueue.candidates() that
blocks release_eligible whenever quality_incident.state == "blocked",
regardless of the status field, so this can never again depend on a
status string accidentally not matching; (3) regression test.
Handoff: if this board still says in-progress after 2026-09-22 19:38 UTC,
the lease has expired -- check git log / this session's own log entry (if
any) for how far it got before picking it up. Unrelated, still open from
earlier entries: release-readiness.yml can hit a genuine git rebase
conflict on public/aion-release-readiness.json (self-healing, not
urgent); creator-scene-production.yml's "scene-generation-unavailable" is
working-as-intended, not a bug. Also worth checking in 1-2 days: does the
evidence-gathering throughput fix (research_batch, learning-cycle.yml
--limit 5) actually translate into new episodes reaching
content/creator_series/*.json.
