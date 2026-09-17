"""Publish one named, quality-gated Studio Short to Instagram and Facebook."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_episode_crosspost import CreatorEpisodeCrosspost
from brain.thinker import Thinker

parser = argparse.ArgumentParser()
parser.add_argument("--episode-id")
parser.add_argument("--latest-published", action="store_true")
args = parser.parse_args()

if bool(args.episode_id) == bool(args.latest_published):
    raise SystemExit("Specify exactly one of --episode-id or --latest-published")
crosspost = CreatorEpisodeCrosspost(Thinker().memory, ROOT)
report = (crosspost.publish_once(args.episode_id) if args.episode_id else crosspost.publish_latest_once())
print(json.dumps(report, ensure_ascii=False, indent=2))
# A YouTube Studio cycle can legitimately finish without publishing a new
# public Short.  That is not a delivery fault and must not poison the company
# health board; there is simply nothing new and eligible to cross-post yet.
# Actual partial delivery, credential/platform errors and quality failures
# remain non-zero so the watchdog can still protect the next release.
if report.get("stage") not in {"published", "no-public-creator-short-awaiting-crosspost"}:
    raise SystemExit(report.get("stage") or "creator-crosspost-failed")
