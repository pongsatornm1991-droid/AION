# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 07:16 UTC
Lease expires: 2026-09-22 10:16 UTC
Scope: Follow-up audit after the three flashing-cmd-window fixes below.
Grepping brain/ and tools/ for subprocess.run(/Popen(/call( and
os.system(/os.popen( call sites that invoke an external executable (git,
ffmpeg, ffprobe, etc.) and are reachable from non-CI-only code paths, i.e.
code that can run on the owner's own Windows machine. Any call site missing
the Windows guard gets the same fix as the three below:
`_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0`
plus `creationflags=_NO_WINDOW` on the call. Will run the relevant test
module(s) per touched file, commit per file (or one commit if the set is
small), pull --rebase, push, log the result in ai-session-log.md, and set
this board back to clear.
Handoff: if this board still says in-progress after 2026-09-22 10:16 UTC,
the lease has expired -- treat it as abandoned and check git log / this
session's own log entry (if any) for how far it got before picking it up.
