# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 17:07 UTC
Lease expires: 2026-09-22 19:07 UTC
Scope: Owner explicitly authorized releasing 3 specific already-produced
episodes found idle during the pipeline audit
(aion-wonders-003-roman-nobody, aion-longform-001-yakhchal both
long-form/upload-ready; aion-auto-85365510840c-00c30e5d, the
octopus-topic short suspected of duplicating an already-published
episode), and said explicitly that if it turns out duplicate they will
check and handle it manually themselves. Publishing the two genuinely
upload-ready long-form episodes via the existing audited CLI pipeline
(prepare-youtube-creator -> quality-youtube-creator ->
run-youtube-creator-publish, --content-kind long-form, run locally with
the owner's own already-configured .env credentials -- same commands the
automation itself uses, just invoked directly for a manual release,
exactly what youtube-creator.yml's own episode_id input describes).
Before touching the octopus one: compared it against the already-published
aion-special-octopus-chromatophores-v1 -- same wonder_hook wording ("how
can an octopus change color... quickly/in seconds"), one literally shared
source URL (oceanexplorer.noaa.gov's same gallery page), no visual_style
assigned at all (never reached that pipeline stage), status
quality-blocked-story-and-audio (a value nothing in the current codebase
still sets -- likely an orphaned pre-refactor record, not an active
quality verdict). This is strong evidence of a real duplicate, not a false
positive. Not publishing it; reporting the specific evidence back to the
owner instead, matching their own stated fallback plan.
Handoff: if this board still says in-progress after 2026-09-22 19:07 UTC,
the lease has expired -- check git log / this session's own log entry (if
any) for how far it got before picking it up. Still open from earlier
entries: release-readiness.yml can hit a genuine git rebase conflict on
public/aion-release-readiness.json (self-healing, not urgent);
creator-scene-production.yml's "scene-generation-unavailable" is
working-as-intended, not a bug. Also worth checking in 1-2 days: does
yesterday's evidence-gathering throughput fix (research_batch,
learning-cycle.yml --limit 5) actually translate into new episodes
reaching content/creator_series/*.json.
