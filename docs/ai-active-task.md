# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude (Cowork)
Started: 2026-09-22 10:26 UTC
Lease expires: n/a
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
