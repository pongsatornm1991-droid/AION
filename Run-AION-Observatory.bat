@echo off
cd /d "%~dp0"

rem See Start-AION-Observatory.bat for what .env.memory_sync does.
if exist ".env.memory_sync" (
    start "AION Memory Sync" /min python tools\sync_memory_from_github.py
    set "AION_DASHBOARD_MEMORY_ROOT=aion-memory-data-sync"
)

pythonw tools\dashboard.py
