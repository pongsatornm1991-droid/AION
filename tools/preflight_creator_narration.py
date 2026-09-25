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


def preflight(root=ROOT, write_timeline=False):
    reports = []
    # One episode that currently fails a content-policy check must not stop
    # this preflight from measuring every other ready storyboard's timing --
    # see brain/creator_series.py's episodes(skip_invalid=True) docstring.
    for episode in CreatorSeriesRegistry(root).episodes(skip_invalid=True):
        if episode.get("status") != "storyboard-ready-needs-assets":
            continue
        report = NarrationPreflight.repair_episode_timing(episode)
        reports.append(report)
        if write_timeline and report.get("eligible"):
            path = Path(root) / str(episode["file"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            # Persist only a bounded, provenance-preserving repair.  The
            # original narration remains attached to the two replacement
            # beats, so a timing fix can always be audited or revised later.
            payload["scenes"] = episode["scenes"]
            payload["target_duration_seconds"] = episode["target_duration_seconds"]
            if episode.get("narration_timing_repairs"):
                payload["narration_timing_repairs"] = episode["narration_timing_repairs"]
            # A scene split updates these two planning ledgers in place (see
            # NarrationPreflight.repair_episode_timing) so their scene count
            # and roles stay in sync with the revised storyboard. Dropping
            # them here left a stale scene_progression/scene_roles on disk
            # that CreatorSeriesRegistry's VisualNarrativeGate/
            # FactFirstVisualGate checks then rejected on every later run --
            # a real episode got stuck this way (2026-09-25).
            if isinstance(episode.get("visual_narrative"), dict):
                payload["visual_narrative"] = episode["visual_narrative"]
            if isinstance(episode.get("fact_first_visual"), dict):
                payload["fact_first_visual"] = episode["fact_first_visual"]
            durations = report.get("scene_durations") or []
            payload["audio_visual_timeline"] = {
                "version": "audio-driven-v1",
                "source": "narration-preflight",
                "scene_durations": durations,
                "rendered_target_duration_seconds": round(sum(durations), 2),
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blocked = [report.get("episode_id") for report in reports if not report.get("eligible")]
    return {"stage": "narration-preflight-complete", "eligible": not blocked, "reports": reports, "blocked": blocked}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-eligible", action="store_true")
    parser.add_argument("--write-timeline", action="store_true",
                        help="Persist the measured per-scene visual holds before image production.")
    args = parser.parse_args()
    result = preflight(write_timeline=args.write_timeline)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_eligible and not result["eligible"]:
        raise SystemExit("creator-narration-preflight-failed")
