"""Self-heal a missed daily YouTube Creator Studio release.

Why this exists (2026-09-22): youtube-creator.yml's own `schedule:` trigger
(cron "30 13 * * *", i.e. 20:30 Bangkok) silently did not fire for two
consecutive days, even though dozens of this repo's other scheduled
workflows kept firing normally in the same window, no run of it was ever
left queued/in_progress, and the workflow itself was never disabled --
pointing at GitHub's own Actions scheduler dropping this specific cron,
not a bug in this repo's code. automation-health.yml cannot catch this
class of failure: it only reacts to a workflow_run event, and a schedule
that never fires produces no such event to react to.

This script runs frequently (see youtube-release-watchdog.yml) and asks
one narrow question: has youtube-creator.yml produced ANY run yet today,
created at or after its own scheduled hour (in UTC, matching its cron)?
If yes -- success, failure, or still running -- today's slot has already
been handled by the real pipeline and this script does nothing, which is
exactly what keeps it from ever causing a second, redundant publish. Only
a complete absence of today's run is treated as a missed schedule, and
only then does this script dispatch youtube-creator.yml itself through the
Actions API. The target workflow's own `aion-youtube-release` concurrency
group and its candidate-selection logic (brain/youtube_creator_queue.py
only ever offers an episode still at status "upload-ready") are what make
an accidental overlap with a delayed real trigger safe too -- this
script's job is only to make sure at least one attempt happens each day,
never to decide what gets published. The dispatch also sets
youtube-creator.yml's `scheduled_recovery` input so its own strict
human-operator check (fail loudly if an explicit workflow_dispatch didn't
reach YouTube) does not misfire on this routine, automated self-heal --
"nothing new to publish today" must stay a quiet, honest non-event here,
exactly as it already is for a real schedule tick.

Run with: python tools/youtube_release_watchdog.py [--dry-run]
Needs GITHUB_TOKEN with `actions: write` (the default GITHUB_TOKEN already
has this once the calling workflow declares that permission -- no new
secret) and normally GITHUB_REPOSITORY, both set automatically inside a
GitHub Actions job.
"""

import argparse
import json
import os
import sys
from datetime import datetime, time, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_REPO = "pongsatornm1991-droid/AION"
WORKFLOW_FILE = "youtube-creator.yml"
# Mirrors youtube-creator.yml's own `cron: "30 13 * * *"` (20:30 Bangkok).
# A run created at or after this UTC time counts as today's attempt; an
# earlier run (e.g. a late recovery run from the previous day) does not.
SCHEDULED_HOUR_UTC = time(13, 30)
_HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "AION-youtube-release-watchdog (https://github.com/pongsatornm1991-droid/AION)",
}


def _get(url, token):
    req = Request(url, headers={**_HEADERS_BASE, "Authorization": f"Bearer {token}"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _dispatch_run(repo, token):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    # scheduled_recovery=true tells youtube-creator.yml this is a self-heal
    # dispatch, not a human operator explicitly demanding a release right
    # now -- without it, its own workflow_dispatch strict check turns an
    # honest "nothing new to publish today" into a red failure (found
    # 2026-09-22, the watchdog's very first real dispatch).
    payload = {"ref": "main", "inputs": {"scheduled_recovery": "true"}}
    req = Request(
        url, method="POST", data=json.dumps(payload).encode("utf-8"),
        headers={**_HEADERS_BASE, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urlopen(req, timeout=30) as resp:
        return resp.status


def todays_attempt_exists(runs, now):
    """True if any run was created today at or after the scheduled UTC hour."""
    today = now.date()
    threshold = datetime.combine(today, SCHEDULED_HOUR_UTC, tzinfo=timezone.utc)
    for run in runs:
        created = run.get("created_at")
        if not created:
            continue
        created_at = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if created_at.date() == today and created_at >= threshold:
            return True
    return False


def check(repo, token, now=None, dry_run=False, fetch_runs=None, dispatch=None):
    """Dispatch youtube-creator.yml only if today's schedule never fired."""
    now = now or datetime.now(timezone.utc)
    if now.time() < SCHEDULED_HOUR_UTC:
        return {"stage": "too-early"}
    fetch_runs = fetch_runs or (lambda: _get(
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=10",
        token,
    ).get("workflow_runs", []))
    runs = fetch_runs()
    if todays_attempt_exists(runs, now):
        return {"stage": "already-attempted-today"}
    if dry_run:
        return {"stage": "would-dispatch-missed-schedule"}
    dispatch = dispatch or (lambda: _dispatch_run(repo, token))
    dispatch()
    return {"stage": "dispatched-missed-schedule"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Report what would happen without dispatching anything.")
    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set -- cannot check or dispatch workflow runs", file=sys.stderr)
        sys.exit(1)

    try:
        result = check(repo, token, dry_run=args.dry_run)
    except (HTTPError, URLError) as exc:
        print(f"Failed to check/dispatch {WORKFLOW_FILE}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
