# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-22 05:10 UTC
Lease expires: n/a
Scope: STILL OPEN -- the repeating-cmd-window bug (first reported when the
owner ran Start-AION-Observatory.bat). Two prior fixes landed and were
pulled by the owner (tools/sync_memory_from_github.py commit e765841;
brain/video_quality.py commit 5ab185a/1498ea6), but the owner confirmed
after both that the flashing was "ยังไม่หายเลย" (still there, no change at
all). That is a strong signal a THIRD source exists that neither prior fix
touched.
Found it (not yet committed -- see below): tools/dashboard.py calls
OperationsControlTower(...).snapshot() on every page load (lines 901 and
996). snapshot() calls its own _audio_timing() method
(brain/operations_control.py:142), which loops over every episode that has
an existing narration .mp3 and calls tools/reel_render.py's
_audio_duration() for each one -- an unguarded
`subprocess.run([ffmpeg, ...])` per episode, every page load. This file
was WRONGLY written off as "not imported by tools/dashboard.py" during the
video_quality.py fix (previous entry in this file) -- that check only
traced brain/video_quality.py's own importers and missed this separate
path, and it also only walked top-level imports; the real import is a
local (in-function) `from tools.reel_render import _audio_duration` inside
_audio_timing(), which a naive "grep for top-level imports" check misses.
Fixed all 3 subprocess.run() call sites in tools/reel_render.py with the
same sys.platform=="win32"-guarded CREATE_NO_WINDOW pattern already used
in the other two files. Ran the full relevant test set (test_reel_render,
test_operations_control, test_audio_visual_timing, test_reels -- 22
passed).
BLOCKED ON COMMIT: something on the owner's machine is holding/recreating
`.git/index.lock` continuously right now (15 straight retry attempts from
this session all failed with "Another git process seems to be running").
This is NOT a stale leftover lock (those were cleared earlier this same
session with a simple mv) -- something is actively re-acquiring it. The
fix is saved on disk at tools/reel_render.py (device_bash writes directly
to the owner's real files) but is NOT YET a git commit. The owner needs to
either (a) close whatever program has this repo open and is polling it
(VS Code with the Git panel open, GitHub Desktop, TortoiseGit, etc.), or
(b) just commit+push it themselves from their own terminal -- their
terminal has had zero lock trouble all session, so it is likely only this
sandboxed session's device_bash racing against that other process, not a
problem for the owner's own shell.
Files touched, not yet committed: `tools/reel_render.py`,
`docs/ai-active-task.md` (this file), `docs/ai-session-log.md`.
Handoff: read `AGENTS.md` and the last 10 session-log entries before
working. Before declaring this bug fixed, get the owner to actually
confirm it empirically (run Start-AION-Observatory.bat, watch for
flashing) -- two "should be the last one" fixes have already turned out to
be incomplete, so treat a third static-analysis fix with the same caution
until it's been verified live. If it recurs a 4th time, do NOT repeat
static code reading again -- use a live Windows-native process trace
(Process Monitor, or a PowerShell WMI Win32_Process creation-event
watcher) while running the .bat, to see the actual offending command
line and its parent process directly, instead of guessing from source.
