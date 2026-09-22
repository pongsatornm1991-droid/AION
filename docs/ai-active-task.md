# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude Code
Started: 2026-09-22 15:21 UTC
Lease expires: n/a
Scope: RESOLVED. Owner asked why no clip published today, then asked to
make the YouTube release pipeline 100% automatic with no duplicate runs.
Root-caused via the GitHub Actions API (not a guess): youtube-creator.yml's
own cron (20:30 Bangkok daily) had not fired in 2 days, even though dozens
of other scheduled workflows in this repo fired normally in the same
window; its two concurrency-group siblings (youtube-release-recovery.yml,
youtube-longform.yml) showed the identical stopped-firing pattern; none of
the three was disabled and none had a run stuck queued/in_progress. Root
cause is GitHub's own Actions scheduler silently not dispatching these
specific crons -- not a bug in this repo's code -- and automation-health.yml
structurally cannot catch it (it only reacts to a workflow_run event; a
schedule that never fires produces no such event at all).
Separately found and fixed a real bug while tracing this: brain/
release_readiness.py counted an episode as "available" via its
`is_authorized` branch without also excluding one that had since actually
been published, so the Shorts buffer overreported readiness by 1 (Venus
flytrap, published 2026-09-21, still shown as available a day later). The
real publish-selection path was never at risk -- confirmed reporting bug,
not a duplicate-publish risk.
Shipped: (1) release_readiness.py now skips status == "published" outright,
regression test added; (2) tools/youtube_release_watchdog.py +
.github/workflows/youtube-release-watchdog.yml, an independently-scheduled
watchdog that dispatches youtube-creator.yml via the Actions API only when
no run of it exists yet today past its scheduled hour -- that gate is what
makes it structurally unable to cause a duplicate/extra publish; (3) wired
into automation-health.yml's failure watch list; (4) 8 new unit tests, all
offline; (5) deliberately did NOT touch instagram-cycle.yml/
social-cycle.yml/reel-cycle.yml -- their own header comments confirm each
is intentionally workflow_dispatch-only, superseded by the Creator Studio
pipeline, not a gap. Full run_tests.py green throughout. See
docs/ai-session-log.md's 2026-09-22 entry (second one) for full detail.
Handoff: read AGENTS.md and the last 10 session-log entries before working.
Follow-up worth watching: the new watchdog's first real scheduled tick had
not yet been observed as of this entry. Check tomorrow whether it correctly
no-ops (if youtube-creator.yml's own cron resumed on its own) or correctly
dispatches (if it's still silent) -- either is fine by design, but worth
confirming the new workflow behaves as intended under real conditions, not
just its offline unit tests. Unrelated, still open from earlier entries:
release-readiness.yml can hit a genuine git rebase conflict on
public/aion-release-readiness.json (self-healing, not urgent);
creator-scene-production.yml's "scene-generation-unavailable" is
working-as-intended, not a bug. Neither touched by this entry.
