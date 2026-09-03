"""Publish a small, PUBLIC summary of every GitHub Actions workflow's
latest run, so the AION Pulse status page can show real system health
without any client-side call to api.github.com.

Why this exists (2026-09-03, second half of the same day as
publish_public_summary.py): AION Pulse (a page published through the
Artifact platform) turned out to be unable to make ANY network call
from the viewer's own browser at all -- not to api.github.com, not
even to raw.githubusercontent.com -- a platform-level security
restriction on published pages, discovered live when the user opened
the page and both of its sections showed a generic fetch failure, not
just the brain section's expected "not published yet" message. The
fix: nothing the page's own JavaScript does can reach the network, so
all data has to be baked into the page at PUBLISH time instead, by
Claude re-rendering and republishing the static HTML on a schedule.
That still needs a source for "is every workflow green right now,"
and this device bridge's own container is *separately* blocked from
calling api.github.com directly (its outbound proxy asks for a
GitHub App "add_repo" grant that is not available in this session
type) -- but GitHub Actions itself has neither restriction: the
built-in GITHUB_TOKEN already has read access to this very repo's own
Actions run history, no extra secret, no separate credential, and
none of the unauthenticated 60-requests/hour cap the old (now-removed)
client-side fetch used to hit. So this script runs here instead, and
its output -- workflow file names, timestamps, and a plain
success/failure/running status, nothing else -- is exactly as safe to
publish into this already-public repo as aion-brain-summary.json is.

Run with: python tools/publish_workflow_status.py [--out public/aion-workflow-status.json]
Needs GITHUB_TOKEN (and normally GITHUB_REPOSITORY) in the
environment -- both set automatically inside a GitHub Actions job.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "public" / "aion-workflow-status.json"
DEFAULT_REPO = "pongsatornm1991-droid/AION"

# Mirrors the category grouping the old client-side JS used to do in
# the browser (now retired -- see the module docstring) so the
# rendered page keeps the same, already-familiar layout.
CATEGORIES = [
    ("post", "เนื้อหา & โพสต์", {
        "social-cycle.yml", "instagram-cycle.yml", "reel-cycle.yml",
        "crosspost-latest-reel.yml", "youtube-shorts.yml",
    }),
    ("think", "ความคิด & การเรียนรู้", {
        "reflection-cycle.yml", "learning-cycle.yml",
        "youtube-learning.yml", "self-narrative.yml",
    }),
    ("approve", "การอนุมัติ & ความปลอดภัย", {
        "check-comments.yml", "check-profile-approvals.yml",
        "propose-profile-change.yml",
    }),
    ("growth", "การเติบโต", {"growth-pulse.yml", "evolution-cycle.yml"}),
    ("infra", "โครงสร้างพื้นฐาน", {
        "tests.yml", "automation-health.yml", "obsidian-brain.yml",
        "publish-public-summary.yml", "publish-workflow-status.yml",
    }),
]
OTHER_KEY, OTHER_LABEL = "other", "อื่นๆ"


def category_for(path):
    fname = (path or "").rsplit("/", 1)[-1]
    for key, label, names in CATEGORIES:
        if fname in names:
            return key, label
    return OTHER_KEY, OTHER_LABEL


def pill_for(run):
    if run is None:
        return "unknown", "ไม่มีข้อมูล"
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status in ("in_progress", "queued"):
        return "running", "กำลังรัน"
    if conclusion == "success":
        return "success", "สำเร็จ"
    if conclusion in ("failure", "timed_out", "startup_failure"):
        return "failure", "ล้มเหลว"
    if conclusion == "cancelled":
        return "unknown", "ยกเลิก"
    return "unknown", conclusion or status or "ไม่ทราบสถานะ"


def fetch_runs(repo, token):
    """Two pages of 100 is the same window the old client-side fetch
    used; a failure on either page is fatal (caller decides what to
    do with a stale/missing output rather than silently publishing a
    half-empty status)."""
    runs = []
    for page in (1, 2):
        url = (
            f"https://api.github.com/repos/{repo}/actions/runs"
            f"?per_page=100&page={page}"
        )
        req = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AION-status-publisher (https://github.com/pongsatornm1991-droid/AION)",
        })
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        runs.extend(data.get("workflow_runs", []))
    return runs


def build_status(runs):
    latest = {}
    for run in runs:
        key = run.get("path") or run.get("name")
        prev = latest.get(key)
        if prev is None or run.get("created_at", "") > prev["run"].get("created_at", ""):
            latest[key] = {
                "name": run.get("name") or ((key or "?").rsplit("/", 1)[-1]),
                "path": run.get("path"),
                "run": run,
            }

    entries = list(latest.values())
    total = len(entries)
    ok = sum(
        1 for e in entries
        if e["run"].get("conclusion") == "success" and e["run"].get("status") != "in_progress"
    )
    running = sum(1 for e in entries if e["run"].get("status") in ("in_progress", "queued"))
    attn = sum(
        1 for e in entries
        if e["run"].get("conclusion") in ("failure", "timed_out", "startup_failure")
    )

    groups = {}
    for e in entries:
        key, label = category_for(e["path"])
        g = groups.setdefault(key, {"key": key, "label": label, "items": []})
        cls, plabel = pill_for(e["run"])
        run = e["run"]
        fname = (e["path"] or "").rsplit("/", 1)[-1]
        g["items"].append({
            "name": e["name"],
            "file": fname,
            "status_class": cls,
            "status_label": plabel,
            "html_url": run.get("html_url"),
            "created_at": run.get("created_at"),
        })

    for g in groups.values():
        g["items"].sort(key=lambda i: i["name"])

    ordered_keys = [c[0] for c in CATEGORIES] + [OTHER_KEY]
    ordered_groups = [groups[k] for k in ordered_keys if k in groups]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tiles": {"total": total, "ok": ok, "attn": attn, "running": running},
        "groups": ordered_groups,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set -- cannot fetch workflow runs", file=sys.stderr)
        sys.exit(1)

    try:
        runs = fetch_runs(repo, token)
    except (HTTPError, URLError) as exc:
        print(f"Failed to fetch workflow runs: {exc}", file=sys.stderr)
        sys.exit(1)

    status = build_status(runs)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} "
        f"({status['tiles']['total']} workflows, {status['tiles']['attn']} need attention)"
    )


if __name__ == "__main__":
    main()
