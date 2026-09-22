# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-22 06:00 UTC
Lease expires: n/a
Scope: RESOLVED, owner-confirmed. The repeating-cmd-window bug reported when
running Start-AION-Observatory.bat had THREE independent causes, found and
fixed one at a time because each earlier fix was real but only partial:
1. tools/sync_memory_from_github.py's git calls (commit e765841)
2. brain/video_quality.py's ffprobe/ffmpeg calls, fired on every dashboard
   page load via tools/dashboard.py -> _next_studio_release() (commit
   5ab185a / merged as 1498ea6)
3. tools/reel_render.py's ffmpeg calls, fired on every dashboard page load
   via tools/dashboard.py -> OperationsControlTower.snapshot() ->
   _audio_timing() -> _audio_duration() (commit dfbebce / merged as
   419ce7f)
All three were the same class of bug: subprocess.run() on Windows without
creationflags=subprocess.CREATE_NO_WINDOW flashes an empty console window
per call. Owner confirmed after all three landed and a fresh
Start-AION-Observatory.bat run: "หายแล้ว" (gone).
Also worth noting for future debugging in this repo: mid-session, git
operations against this exact repo (both via the desktop bridge AND the
owner's own terminal) repeatedly hit "Unable to create .git/index.lock:
File exists" / stale swap files. Root cause turned out to be mundane: the
owner had another bot running that was itself touching this repo's git
state at the same time. Once they stopped it, commits/pushes went through
normally. If this recurs, ask what else might be running against the repo
before assuming a deeper problem.
Handoff: read AGENTS.md and the last 10 session-log entries before working.
Separately, still open from the earlier commit-and-push investigation
(2026-09-22, see session log): release-readiness.yml can hit a genuine git
rebase conflict on public/aion-release-readiness.json (self-healing, not
urgent); creator-scene-production.yml's "scene-generation-unavailable" is
working-as-intended, not a bug. Neither is touched by this entry.
2026-09-22 06:40 UTC verification pass (see session log for full detail):
both remaining "attn" tiles on the dashboard checked against live run
history. reel-cycle.yml's duplicate-OPENAI_API_KEY YAML error was already
fixed by commit 87cf99a; the tile is just stale (workflow_dispatch-only,
nobody re-ran it since the fix) -- a manual re-run would clear it but
nothing needs fixing. creator-scene-production.yml is still hitting the
same known scene-generation-unavailable gate, unchanged from the prior
finding. No code changes made this pass. No task currently needs the
separate Claude Code session; do not run it concurrently with this
session against the same repo (that caused this session's earlier git
lock contention).
