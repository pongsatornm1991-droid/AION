# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude Code
Started: 2026-09-22 19:53 UTC
Lease expires: n/a
Scope: RESOLVED (multiple small tasks this session; see
docs/ai-session-log.md for full detail on each). Venus release-readiness
staleness is now actually fixed at the source (pushed a corrected
youtube_creator_queue.md record straight to aion-memory-data's real main
branch, not just the owner's local copy) -- no longer a pending item.
Also had an extended channel-naming and visual-style discussion with the
owner; NOT code, but two things anyone picking up branding/creative work
needs to know before touching it:
1. Channel rename is still an OPEN decision -- do not assume a name has
   been chosen. Leading candidate discussed: "Wait, How?". See the
   session log's "Channel-naming and visual-style discussion" entry for
   the full reasoning (SEO collision with the current name "Aion I Robot"
   / the film "I, Robot"; a fair owner challenge on whether "AION" needs
   to be in the channel name at all, given "Aion" itself collides with an
   existing MMORPG). Ask the owner directly rather than pick for them.
2. Visual style is CONFIRMED, closed, do not reopen: `aion-neon-diorama-
   3d-v1` (glossy 3D neon diorama) is the real channel signature, decided
   before this session (commits cfdef81/7c9862c) and re-confirmed by the
   owner mid-session after this session wrongly suggested reconsidering
   it toward flat-2D-vector. Don't suggest that again without a new,
   specific reason.
Handoff: read AGENTS.md and the last 10 session-log entries before
working -- there are a lot from today. Concretely still open: (1) a
newly-qualifying evidence group was observed failing
CreatorSourceIntegrity's check in real time today -- worth checking
whether that gate is now too strict for the 5x research throughput
increase shipped today, or working as intended; (2) confirm the two
long-form episodes published today (aion-longform-001-yakhchal,
aion-wonders-003) actually carry a real, current visual_style rather than
an unset/legacy one; (3) the long-form template's "compare" bridge beat
still has the generic-filler shape the short-form beats had before
today's fixes -- low priority, Shorts is the daily focus now; (4) check
in a day or two whether the evidence-throughput fix (research_batch,
learning-cycle.yml --limit 5) actually produces a new episode in
content/creator_series/*.json -- none had as of this entry. Unrelated,
still open from earlier entries: release-readiness.yml can hit a genuine
git rebase conflict on public/aion-release-readiness.json (self-healing,
not urgent); creator-scene-production.yml's "scene-generation-unavailable"
is working-as-intended, not a bug.
