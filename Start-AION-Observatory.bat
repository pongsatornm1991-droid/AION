@echo off
cd /d "%~dp0"
start "AION Observatory" /min pythonw tools\dashboard.py
start "" http://127.0.0.1:8787
