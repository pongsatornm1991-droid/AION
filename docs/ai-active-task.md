# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 15:21 UTC
Lease expires: 2026-09-22 19:21 UTC
Scope: Owner asked why no clip published today, then asked to make the
YouTube release pipeline 100% automatic with no duplicate runs. Root-caused
via the GitHub Actions API (not a guess): youtube-creator.yml's own cron
(20:30 Bangkok daily) has not actually fired in 2 days, even though dozens
of other scheduled workflows in this repo fired normally in the same
window; its two concurrency-group siblings (youtube-release-recovery.yml,
youtube-longform.yml) show the identical stopped-firing pattern; none of
the three are disabled and none has a run stuck queued/in_progress. Root
cause is GitHub's own Actions scheduler silently not dispatching these
specific crons -- not a bug in this repo's code -- and automation-health.yml
structurally cannot catch it (it only reacts to a workflow_run event; a
schedule that never fires produces no such event at all).
Separately found a real bug while tracing this: brain/release_readiness.py
counts an episode as "available" via its `is_authorized` branch
(publication_status == authorized-for-aion-publish) without also excluding
one that has since actually been published, so the Shorts buffer has been
overreporting readiness by 1 (Venus flytrap, published 2026-09-21, still
shown as available at itself). The real publish-selection path
(YouTubeCreatorQueue.prepare_once()'s `eligible` filter) already checks
`status == "upload-ready"` correctly and is NOT at risk of a duplicate
publish -- this is a reporting bug, not a live double-post risk.
Plan: (1) fix release_readiness.py's exclusion + regression test; (2) add
a new, independently-scheduled watchdog (tools + workflow) that checks
whether youtube-creator.yml has produced any run yet today past its
scheduled hour, and if genuinely none exists, dispatches it itself via the
Actions API (GITHUB_TOKEN, actions:write) -- self-healing against GitHub's
scheduler dropping the cron, while the "any run already exists today" gate
is exactly what prevents it from ever causing a duplicate/extra run; (3)
wire the new workflow into automation-health.yml's failure watch list; (4)
tests for both; (5) explicitly NOT touching instagram-cycle.yml/
social-cycle.yml/reel-cycle.yml -- read their own header comments and
confirmed these are deliberately workflow_dispatch-only, superseded by the
Creator Studio pipeline, not a gap.
Handoff: if this board still says in-progress after 2026-09-22 19:21 UTC,
the lease has expired -- check git log / this session's own log entry (if
any) for how far it got before picking it up.
Scope: RESOLVED. Owner asked why the Shorts release buffer was stuck at
1/7 ready despite the 2026-09-21 move to a daily production+publish
cadence, and asked for a fix so production does not wait in a queue.
Traced the pipeline: research-to-story.yml (every 3h) chains three
steps -- ResearchToStory.propose_once(), ResearchStoryHandoff.create_once(),
StoryEpisodeStager.stage_once() -- and every one of them converted only
ONE eligible item per run, even when multiple already-qualified items
(candidates/briefs/handoffs) were sitting ready. That is an arbitrary
per-run throughput cap, not a quality gate (all existing evidence,
novelty, Fact-First Visual and Watchability gates are untouched). Added
propose_batch()/create_batch()/stage_batch() bounded-loop variants
(limit defaults to 5, mirroring CreatorSceneProduction's existing
produce_ready_episodes() pattern) to all three brain/ classes, wired
tools/run_research_to_story.py, tools/run_research_story_handoff.py and
tools/stage_creator_episode.py to call the batch variant with --limit,
and left stage_once()/propose_once()/create_once() themselves untouched
(still used by tools/recover_release_buffer.py and existing tests) so
this is additive, not a behavior change to any other caller. Added 3
new unit tests (2-item batches) covering all three stages. Full
targeted suite green; full run_tests.py shows the same 5 pre-existing
unrelated failures/errors as every prior check this session. See
docs/ai-session-log.md's 2026-09-22 entry for full detail.
Handoff: read AGENTS.md and the last 10 session-log entries before working.
Follow-up worth watching: this only removes the artificial per-run cap;
it does not guarantee 7 qualified evidence groups exist upstream on any
given day (evidence-gathering workflows still run every 6h). Check the
buffer again in 2-3 days -- if it is still stuck well below target with
this fix live, the real constraint is evidence *volume*, not this
per-run cap, and the fix would need to look further upstream (the
6-hourly research/evidence workflows themselves). Still open from
earlier entries: release-readiness.yml can hit a genuine git rebase
conflict on public/aion-release-readiness.json (self-healing, not
urgent); creator-scene-production.yml's "scene-generation-unavailable"
is working-as-intended, not a bug. Neither touched by this entry.
