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
parser.add_argument("--episode-id", required=True)
args = parser.parse_args()

report = CreatorEpisodeCrosspost(Thinker().memory, ROOT).publish_once(args.episode_id)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report.get("stage") not in {"published", "partially-published"}:
    raise SystemExit(report.get("stage") or "creator-crosspost-failed")
