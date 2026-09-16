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
if report.get("stage") != "published":
    raise SystemExit(report.get("stage") or "creator-crosspost-failed")
