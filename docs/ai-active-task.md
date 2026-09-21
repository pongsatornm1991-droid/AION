# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-21 20:10 Asia/Bangkok
Lease expires: n/a
Scope: RESOLVED (second pass) -- owner reported "ยังเด้ง" (still flashing) after
pulling and restarting with the first fix (tools/sync_memory_from_github.py,
commit e765841). That fix was real but not the primary source: owner had
already confirmed via tasklist that no python.exe/pythonw.exe process was even
running when the flashing was observed, meaning it wasn't coming from the
45s-interval background sync loop at all. Re-traced the actual trigger:
opening the dashboard (tools/dashboard.py) calls _next_studio_release(), which
loops release-queue candidates and calls VideoQualityGate(ROOT).assess(...)
per candidate -- up to 4 unguarded ffprobe/ffmpeg subprocess.run() calls each,
fired synchronously on every dashboard page load. That is a far better match
for the symptom (a burst of blank cmd windows right when the dashboard opens,
not once every 45s from a loop that wasn't running). Fixed the same way: added
creationflags=subprocess.CREATE_NO_WINDOW to all 3 self.runner(...) call sites
in brain/video_quality.py, guarded by sys.platform == "win32" (no-op on Linux
CI, verified safe with a direct interpreter check before editing). Ran the
full set of tests that exercise VideoQualityGate: test_video_quality.py (4),
test_assemble_creator_episode.py, test_creator_episode_crosspost.py,
test_youtube_creator_queue.py, test_youtube_cycle.py -- 35 passed total, no
mocking of runner needed since the guard is a no-op on Linux.
Also audited brain/ and tools/ for other unguarded subprocess.run() calls:
found more in tools/reel_render.py and tools/produce_creator_motion.py, but
neither is imported by tools/dashboard.py (confirmed via import grep), so
they don't fire on dashboard page load and are out of scope for this
specific symptom -- left untouched.
Files: `brain/video_quality.py`, `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log
entries, and this board before working. If the owner reports the dashboard
*still* flashes windows after this fix + a git pull, the next place to look is
whichever code path actually ran at that moment -- ask what the owner was
doing right before it happened (opening the dashboard vs. running the .bat
launcher vs. something else), since two separate root causes have already
been found and fixed in this exact bug report and a third is plausible
(e.g. the .bat launcher's own use of `start` / python invocation, which
hasn't been audited yet -- Start-AION-Observatory.bat itself was never
inspected in this investigation, only the two subprocess-calling Python
files it eventually triggers).
