# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude (Cowork)
Started: 2026-09-22 09:23 UTC
Lease expires: n/a
Scope: RESOLVED. Added a second neon house style, aion-neon-diorama-3d-v1
(glossy 3D miniature-diorama rendering, same neon palette as the flat
aion-neon-vector-shorts-v1 preset), to
CreatorSceneProduction._style_rule(). Generalized _cover_prompt()'s
previously-hardcoded single-id check into
_REPLACES_COLOR_DIRECTION_STYLE_IDS so any future "replaces the shared
colour direction" preset only needs adding to that set. Promoted the new
3D preset to VisualStoryPolicy.CHANNEL_VISUAL_STYLE (the channel's
signature default for new auto-staged episodes) at the owner's explicit
request after comparing real generated previews of both styles side by
side. The flat-vector preset stays a valid style id for older/manually
placed episodes. 2 new unit tests added; full targeted suite green; full
run_tests.py shows the same 5 pre-existing unrelated
failures/errors (test_dashboard x2, test_direct_message x1,
test_new_workspaces x1, test_self_improvement_resilience x1 -- all
environment/lock-file artifacts of this connected-folder mount, confirmed
unrelated by traceback before this change too). See
docs/ai-session-log.md's 2026-09-22 entry for full detail.
Handoff: read AGENTS.md and the last 10 session-log entries before working.
No known follow-up needed for this specific change. Still open from
earlier entries: release-readiness.yml can hit a genuine git rebase
conflict on public/aion-release-readiness.json (self-healing, not
urgent); creator-scene-production.yml's "scene-generation-unavailable" is
working-as-intended, not a bug. Neither touched by this entry.
