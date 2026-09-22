# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 18:54 UTC
Lease expires: 2026-09-22 20:54 UTC
Scope: Owner confirmed the channel is Shorts-only now and asked what to
develop next, then said do all of it immediately. Recommended and now
implementing: (1) a stronger hook (was "Today we are asking: {topic}" on
every single episode -- now leads with a real sourced fact, then the
question); (2) a stronger ending (was "Keep asking better questions, and
check the evidence with me" verbatim on every episode -- now closes on the
actual topic instead of a generic sign-off, still never ending on "?" per
WatchabilityGate); both in StoryEpisodeStager's short-form template, the
one that actually matters now that long-form isn't the daily focus.
4 new regression tests, full run_tests.py green.
Also investigated the still-open Venus release-readiness staleness (flagged
in earlier entries): confirmed it needs `reconcile-youtube-creator` run
against the real private memory repo, which only the owner can do locally
(this sandbox has no access to that repo, and this project's own
youtube-publication-drift.yml is deliberately a detector-only design --
reconciliation is intentionally kept a human, one-video-at-a-time decision
after a 2026-09-21 near-miss, not something to automate around). Will hand
the owner the exact ready-to-run command rather than build new automation
that would undercut that existing safety design.
Confirmed, no code change needed: the daily automated cadence
(youtube-creator.yml) already defaults to content-kind=short only --
Shorts-only is already how the automation runs today.
Handoff: if this board still says in-progress after 2026-09-22 20:54 UTC,
the lease has expired -- check git log / this session's own log entry (if
any) for how far it got before picking it up. Unrelated, still open:
public/aion-release-readiness.json still shows aion-wonders-005-venus-
flytrap-counts as available -- needs the owner to run
reconcile-youtube-creator locally (exact command in the session log/chat).
release-readiness.yml can hit a genuine git rebase conflict on that same
file (self-healing, not urgent); creator-scene-production.yml's
"scene-generation-unavailable" is working-as-intended, not a bug. Also
worth checking in 1-2 days: does the evidence-gathering throughput fix
(research_batch, learning-cycle.yml --limit 5) actually translate into new
episodes reaching content/creator_series/*.json. Not done, flagged only:
the long-form template's own generic "compare" bridge beat has the same
shape the short-form "connection" beat had -- lower priority now that
Shorts is the daily focus, left untouched.
