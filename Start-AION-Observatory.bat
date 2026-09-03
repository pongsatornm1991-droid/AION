@echo off
cd /d "%~dp0"

rem If you have set up .env.memory_sync (see .env.memory_sync.example),
rem also keep a local clone of the private aion-memory-data repo fresh
rem in the background, and point the dashboard at it -- otherwise the
rem dashboard falls back to this machine's own local memory/ folder,
rem same as before.
if exist ".env.memory_sync" (
    start "AION Memory Sync" /min python tools\sync_memory_from_github.py
    set "AION_DASHBOARD_MEMORY_ROOT=aion-memory-data-sync"
)

start "AION Observatory" /min pythonw tools\dashboard.py
start "" http://127.0.0.1:8787
