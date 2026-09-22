# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-22 03:33 UTC
Lease expires: n/a
Scope: RESOLVED (partial) -- owner connected a separate Claude Code session
that scanned the repo and reported "workflow ล้มเหลวพร้อมกันที่ขั้นตอน
commit-and-push" across 11 runs, with a working theory of push-retry
exhaustion (not enough attempts/jitter for the commit frequency). That
theory does not survive a timing check: every failing run's commit-and-push
step completed in 0-1 seconds, which rules out a chain whose fallbacks
sleep 10s then 20s between attempts -- a real retry exhaustion would show
at least ~30s of step duration.
Read the real logs instead (via the owner's own logged-in browser -- job
log downloads 403 without repo-admin auth, confirmed again this session).
Found THREE distinct, unrelated failure modes bundled under that one
"commit-and-push failed" label:
1. (FIXED, commit 2efbe45) .github/actions/commit-and-push/action.yml's
   mkdir-parent-directory loop calls `dirname "$path"`. Every workflow that
   passes paths: "-A" (9 of the 11 failing runs) hits `dirname: invalid
   option -- 'A'` because dirname treats a leading-dash argument as an
   option, not a filename -- mkdir -p "" then fails, and the step (shell:
   bash defaults to -eo pipefail) aborts before git add/commit/push ever
   runs. That is the real cause of the 0s-duration failures. Fixed with
   `dirname -- "$path"`. Reproduced the crash and verified the fix with
   the exact shell snippet from the file before editing.
2. (NOT fixed, believed self-healing, lower priority) release-readiness.yml
   can hit a genuine `git rebase` content conflict on
   public/aion-release-readiness.json when two near-simultaneous runs of
   that workflow both regenerate it -- confirmed via a real "CONFLICT
   (content): Merge conflict in public/aion-release-readiness.json" in run
   35634789860's log. Not a retry-count problem; a real conflicting diff on
   a machine-generated snapshot file. The next successful run overwrites
   the file fresh, so a single missed refresh is a stale readiness board
   for a few hours, not data loss. Left untouched -- a real fix needs
   either serializing this file's writers more tightly or switching to a
   regenerate-on-conflict strategy (abort rebase, rerun the generator
   against the new HEAD, recommit) rather than trying to text-merge JSON.
3. (NOT a bug, working as intended) creator-scene-production.yml run
   35634638214 failed with a "scene-generation-unavailable" stage --
   brain/creator_scene_production.py deliberately leaves the storyboard
   byte-for-byte untouched and reports this stage when the image-generation
   provider produced nothing, specifically so a failed scheduled run stays
   observable instead of silently looking like it worked. This is a real
   image-provider outage/config issue at that moment, not a code defect;
   the workflow going red is the intended signal.
A fourth run (reel-cycle.yml, run 35634636859) had 0 jobs at all (startup
failure on a `push` trigger) -- a single occurrence, not investigated
further; low priority unless it recurs.
Files this session touched: `.github/actions/commit-and-push/action.yml`,
`docs/ai-active-task.md`, `docs/ai-session-log.md`.
Note for whoever works in this repo next via the desktop bridge: something
on the owner's machine (not this session -- each device_bash call is its
own fresh, isolated process) was repeatedly recreating .git/index.lock
during this session's commit, requiring several retries. Likely an IDE or
git GUI polling this exact repo. Not chased down; mention it to the owner
if git operations here keep stalling.
Handoff: read `AGENTS.md` and the last 10 session-log entries before
working. If failures matching "commit-and-push" recur, check the actual
paths input first (a literal "-A"/"-x"-style flag vs. a real path) before
assuming it is #1 again -- this fix only covers the leading-dash-argument
case. #2 and #3 above are still open and belong to whoever wants to invest
in them next; neither is urgent.
