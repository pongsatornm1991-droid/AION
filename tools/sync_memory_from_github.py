"""Background loop: keep a local clone of the private aion-memory-data
repo up to date, so the local Observatory dashboard (tools/dashboard.py)
can show what AION is actually doing in production -- not just what
this machine's own local memory/ (OneDrive) folder happens to hold.

Why this exists: memory/ on this machine is a personal OneDrive backup
folder (see link_memory_to_onedrive.bat) -- it is NOT the same store
GitHub Actions writes to when AION runs in the cloud. That is the
private aion-memory-data repo: every scheduled workflow checks it out
fresh into memory_data/ at the start of a run and pushes it back at
the end (see any .github/workflows/*.yml's "Checkout AION memory
(private repo)" step). Found 2026-09-03 while investigating why the
Observatory dashboard felt disconnected from AION's real activity --
it was refreshing every 15 seconds, faithfully, from the wrong place.

One-time setup (you do this yourself -- Claude never handles the token):
  1. Copy .env.memory_sync.example to .env.memory_sync
  2. Paste in the SAME fine-grained PAT you already created for the
     MEMORY_REPO_PAT GitHub secret (see docs/GITHUB_ACTIONS_SETUP.md)
     -- it already has Contents: Read and write on aion-memory-data,
     which covers pulling. A separate read-only token works too, if
     you would rather keep them apart.

Run with: python tools/sync_memory_from_github.py
Then point the dashboard at the synced clone (Start-AION-Observatory.bat
does this automatically when .env.memory_sync exists):
  set AION_DASHBOARD_MEMORY_ROOT=aion-memory-data-sync
  python tools/dashboard.py

This script only ever reads from aion-memory-data (clone + pull). It
never pushes, so it can never create the two-writers-racing problem
`.github/workflows/*.yml`'s shared concurrency group exists to prevent.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLONE_DIR = ROOT / "aion-memory-data-sync"
REPO = "pongsatornm1991-droid/aion-memory-data"
ENV_FILE = ROOT / ".env.memory_sync"
DEFAULT_INTERVAL_SECONDS = 45


def _timestamp():
    return time.strftime("%H:%M:%S")


def _load_token():
    """Read MEMORY_REPO_PAT from the environment, then from
    .env.memory_sync (a plain KEY=value file, never printed or logged
    here). Returns None if neither has it."""

    token = os.getenv("MEMORY_REPO_PAT")
    if token:
        return token.strip()

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("MEMORY_REPO_PAT="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


def _run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def _redact(text, token):
    return (text or "").replace(token, "***") if token else (text or "")


def sync_once(token):
    """Clone aion-memory-data if it isn't present yet, otherwise pull.
    Returns True on success, False on failure (never raises -- this is
    a background loop meant to keep running through a transient
    network hiccup)."""

    remote_url = f"https://{token}@github.com/{REPO}.git"

    if not (CLONE_DIR / ".git").exists():
        print(f"[{_timestamp()}] Cloning {REPO} for the first time...")
        result = _run(["git", "clone", remote_url, str(CLONE_DIR)])
    else:
        # Refresh the token in the remote URL every time in case it was
        # rotated, without ever printing or storing it anywhere else.
        _run(["git", "remote", "set-url", "origin", remote_url], cwd=CLONE_DIR)
        result = _run(["git", "pull", "--ff-only"], cwd=CLONE_DIR)

    if result.returncode != 0:
        print(f"[{_timestamp()}] Sync failed: {_redact(result.stderr, token).strip()}")
        return False

    return True


def main():
    token = _load_token()
    if not token:
        print(
            "MEMORY_REPO_PAT not found.\n"
            "Copy tools/.env.memory_sync.example to .env.memory_sync "
            "(project root) and paste in your token, or set the "
            "MEMORY_REPO_PAT environment variable yourself."
        )
        sys.exit(1)

    interval = int(os.getenv("MEMORY_SYNC_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))
    print(f"AION memory sync loop started (every {interval}s). Ctrl+C to stop.")

    while True:
        sync_once(token)
        time.sleep(interval)


if __name__ == "__main__":
    main()
