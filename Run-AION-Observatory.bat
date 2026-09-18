@echo off
cd /d "%~dp0"

rem This legacy launcher must behave exactly like the normal Start launcher.
rem Running pythonw directly made cmd.exe wait for the server forever, leaving
rem a large black command window on screen even though the Observatory worked.
if exist ".env.memory_sync" (
    start "AION Memory Sync" /min python tools\sync_memory_from_github.py
    set "AION_DASHBOARD_MEMORY_ROOT=aion-memory-data-sync"
)

rem Start the local-only server independently, then return to the browser.
start "AION Observatory" /min pythonw tools\dashboard.py
start "" http://127.0.0.1:8787
