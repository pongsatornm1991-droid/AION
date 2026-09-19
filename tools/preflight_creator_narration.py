"""Reject timing-unsafe new Creator storyboards before image production."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_series import CreatorSeriesRegistry
from brain.narration_preflight import NarrationPreflight


def preflight(root=ROOT):
    reports = []
    for episode in CreatorSeriesRegistry(root).episodes():
        if episode.get("status") != "storyboard-ready-needs-assets":
            continue
        reports.append(NarrationPreflight.assess_episode(episode))
    blocked = [report.get("episode_id") for report in reports if not report.get("eligible")]
    return {"stage": "narration-preflight-complete", "eligible": not blocked, "reports": reports, "blocked": blocked}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-eligible", action="store_true")
    args = parser.parse_args()
    result = preflight()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_eligible and not result["eligible"]:
        raise SystemExit("creator-narration-preflight-failed")
