# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Claude
Started: 2026-09-21 19:25 Asia/Bangkok
Lease expires: n/a
Scope: RESOLVED -- owner reported blank cmd windows repeating non-stop after running Start-AION-Observatory.bat locally. Diagnosed via the owner's linked machine (not guesswork): AION's own dashboard/launcher code has no window-spawning loop, but tools/sync_memory_from_github.py's background sync loop (active when .env.memory_sync exists, confirmed present) calls subprocess.run(["git", ...]) every 45s forever -- a classic Windows subprocess.run()-flashes-a-console-window-per-call issue that's invisible for one call but looks like an endless stream for a loop that never stops. Confirmed the loop was genuinely running by finding aion-memory-data-sync/ on the owner's machine with a just-refreshed timestamp. Fixed with creationflags=subprocess.CREATE_NO_WINDOW in _run() (guarded for win32 only, no-op on Linux CI). tests/test_sync_memory.py mocks _run() itself, unaffected, all 6 pass.
Files: `tools/sync_memory_from_github.py`, `docs/ai-active-task.md`, `docs/ai-session-log.md`.
Handoff: The next assistant must read `AGENTS.md`, the last 10 session-log entries, and this board before working. Commits `e765841` (the fix) and `ab21daf` (this entry) are local-only as of this write -- confirm `git push origin main` ran. IMPORTANT for the owner: this fix only takes effect the next time the sync loop starts fresh -- the currently-running background sync process (if still running on their machine) has the old code in memory and will keep flashing windows until it's restarted (close the "AION Memory Sync" cmd window or end the python.exe process, then re-run Start-AION-Observatory.bat after pulling this commit).
