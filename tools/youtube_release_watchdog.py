"""Self-heal a missed YouTube Creator Studio release slot.

Why this exists (2026-09-22): youtube-creator.yml's own `schedule:` trigger
(then a single daily cron, 20:30 Bangkok) silently did not fire for two
consecutive days, even though dozens of this repo's other scheduled
workflows kept firing normally in the same window, no run of it was ever
left queued/in_progress, and the workflow itself was never disabled --
pointing at GitHub's own Actions scheduler dropping this specific cron,
not a bug in this repo's code. automation-health.yml cannot catch this
class of failure: it only reacts to a workflow_run event, and a schedule
that never fires produces no such event to react to.

Extended 2026-09-29 when the owner asked for two release slots a day
(18:00 and 20:30 Bangkok) instead of one: each slot needs this same
self-heal protection independently, so this now reads
brain.channel_policy.ChannelPolicy's `shorts_times` instead of a single
hardcoded hour, and can never silently drift out of sync with
youtube-creator.yml's own cron lines the way two independently-maintained
copies of the schedule eventually would.

This script runs frequently (see youtube-release-watchdog.yml) and asks
one narrow question per configured slot: has youtube-creator.yml produced
a run created within that slot's own window (from the slot's start until
the next slot's start, or now for the day's last slot)? A slot with a run
in its window -- success, failure, or still running -- has already been
handled by the real pipeline, which is exactly what keeps this from ever
causing a second, redundant publish for that same slot. Only a slot whose
window has begun with no run in it at all is treated as missed, and only
then does this script dispatch youtube-creator.yml itself through the
Actions API. The target workflow's own `aion-youtube-release` concurrency
group and its candidate-selection logic (brain/youtube_creator_queue.py
only ever offers an episode still at status "upload-ready") are what make
an accidental overlap with a delayed real trigger safe too -- this
script's job is only to make sure at least one attempt happens per slot
each day, never to decide what gets published. The dispatch also sets
youtube-creator.yml's `scheduled_recovery` input so its own strict
human-operator check (fail loudly if an explicit workflow_dispatch didn't
reach YouTube) does not misfire on this routine, automated self-heal --
"nothing new to publish for this slot" must stay a quiet, honest non-event
here, exactly as it already is for a real schedule tick.

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
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_REPO = "pongsatornm1991-droid/AION"
WORKFLOW_FILE = "youtube-creator.yml"
ROOT = Path(__file__).resolve().parents[1]
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


def _scheduled_hours_utc():
    """Bangkok shorts_times (see brain.channel_policy) as UTC times-of-day,
    matching youtube-creator.yml's own cron lines. Read from the shared
    policy so the two can never silently drift apart the way two
    independently hand-maintained copies of the schedule eventually would.
    Bangkok has no DST, so a fixed UTC+7 offset is always correct.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from brain.channel_policy import ChannelPolicy

    hours = []
    for hhmm in ChannelPolicy(ROOT).publishing()["shorts_times"]:
        hour, minute = (int(part) for part in hhmm.split(":", 1))
        total_minutes = (hour * 60 + minute - 7 * 60) % (24 * 60)
        hours.append(time(total_minutes // 60, total_minutes % 60))
    return sorted(hours)


def slot_windows(scheduled_hours, now):
    """(start, end) for each of today's UTC scheduled hours that has
    already begun. `end` is the next slot's start, or `now` for the day's
    last slot -- bounding each window keeps one dispatch that covers an
    earlier missed slot from being mistaken for also covering a later,
    separately-missed slot."""
    today = now.date()
    starts = sorted(datetime.combine(today, hour, tzinfo=timezone.utc) for hour in scheduled_hours)
    windows = []
    for index, start in enumerate(starts):
        if start > now:
            continue
        end = starts[index + 1] if index + 1 < len(starts) else now
        windows.append((start, end))
    return windows


def todays_attempt_exists(runs, now, scheduled_hours=None):
    """True if every one of today's scheduled slots that has already begun
    has at least one run created within its own window. True (nothing to
    do) when no slot has begun yet today."""
    hours = _scheduled_hours_utc() if scheduled_hours is None else scheduled_hours
    windows = slot_windows(hours, now)
    if not windows:
        return True
    created_ats = [
        datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        for run in runs if run.get("created_at")
    ]
    return all(
        any(start <= created <= end for created in created_ats)
        for start, end in windows
    )


def check(repo, token, now=None, dry_run=False, fetch_runs=None, dispatch=None, scheduled_hours=None):
    """Dispatch youtube-creator.yml only if a scheduled slot today never fired.

    `scheduled_hours` defaults to the real policy (brain.channel_policy);
    tests inject an explicit list to stay deterministic.
    """
    now = now or datetime.now(timezone.utc)
    hours = _scheduled_hours_utc() if scheduled_hours is None else scheduled_hours
    if not slot_windows(hours, now):
        return {"stage": "too-early"}
    fetch_runs = fetch_runs or (lambda: _get(
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=10",
        token,
    ).get("workflow_runs", []))
    runs = fetch_runs()
    if todays_attempt_exists(runs, now, hours):
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
