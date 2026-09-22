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
Scope: RESOLVED (partial by necessity, not left half-done). Owner
authorized releasing 3 idle episodes found in the pipeline audit.
Attempted all 3: aion-longform-001-yakhchal passed prepare+quality
cleanly but publish correctly refused with Stage: invalid-cover (its
cover is 1080x1920, long-form needs widescreen) -- tried the real fix
(regenerating a proper cover via the same generator
creator_scene_production.py itself uses) and it failed because this
sandbox has neither an OpenAI image API key nor the `openai` package,
both of which GitHub Actions has as a repo secret; did not paper over
this with a cropped/reused image since that would produce a genuinely
bad thumbnail, not a real fix. aion-wonders-003 has the identical
cover problem, confirmed but not separately attempted (same fix needed).
aion-auto-85365510840c-00c30e5d (octopus topic): compared directly
against the already-published aion-special-octopus-chromatophores-v1 --
same wonder_hook wording, one identical source URL, no visual_style ever
assigned, and a status value nothing in the current codebase still
writes -- strong evidence of a real duplicate. Withheld, matching the
owner's own stated fallback (they will check and handle it manually).
No upload happened for any of the 3; only harmless local audit-trail
memory records + one episode_number metadata write (verified non-
colliding, kept, see session log). Full run_tests.py green.
Handoff: read AGENTS.md and the last 10 session-log entries before
working. Two of the three releases are blocked on a real, external
infrastructure gap (no local OpenAI image credentials) rather than
anything fixable in this repo's code -- the next session (or the owner,
from a machine/environment with OPENAI_API_KEY configured, or by
triggering creator-scene-production.yml on GitHub Actions where the
secret already exists) needs to regenerate a proper 16:9 cover for both
before their publish can proceed; the prepare/quality audit trail for
yakhchal is already in place so publish can resume directly once that
exists. Still open from earlier entries: release-readiness.yml can hit a
genuine git rebase conflict on public/aion-release-readiness.json
(self-healing, not urgent); creator-scene-production.yml's
"scene-generation-unavailable" is working-as-intended, not a bug. Also
worth checking in 1-2 days: does the evidence-gathering throughput fix
(research_batch, learning-cycle.yml --limit 5) actually translate into
new episodes reaching content/creator_series/*.json.
