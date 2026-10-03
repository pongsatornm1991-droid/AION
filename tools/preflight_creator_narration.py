"""Reject timing-unsafe new Creator storyboards before image production."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_series import CreatorSeriesRegistry
from brain.narration_preflight import NarrationPreflight


def narration_key(episode):
    """Fingerprint of everything that decides an episode's measured timing.

    The measurement synthesizes EVERY scene's line with the paid speech
    provider. This workflow runs 10-14 times a day and used to re-measure
    every waiting storyboard each time even though neither the narration nor
    the voice had changed -- the single largest avoidable speech spend while
    storyboards queue for images. The same text with the same voice measures
    the same, so a stored result keyed on both is reused instead.
    """
    voice = "|".join(os.getenv(name, "") for name in (
        "REEL_VOICE_PROVIDER", "REEL_VOICE", "OPENAI_TTS_MODEL", "OPENAI_TTS_INSTRUCTIONS",
    ))
    lines = "\n".join(str(scene.get("narration") or "").strip() for scene in episode.get("scenes") or [])
    return hashlib.sha256(f"{voice}\n{episode.get('scene_seconds')}\n{lines}".encode("utf-8")).hexdigest()[:24]


def _cached_report(episode):
    """A previous result for this exact narration + voice, or None."""
    key = narration_key(episode)
    timeline = episode.get("audio_visual_timeline") or {}
    scenes = episode.get("scenes") or []
    durations = timeline.get("scene_durations") or []
    if timeline.get("source") == "narration-preflight" and timeline.get("narration_key") == key             and len(durations) == len(scenes):
        return {
            "eligible": True, "state": "pass", "cached": True, "episode_id": episode.get("id"),
            "checks": [], "reasons": [], "scene_durations": durations,
            "timing_repair": {"attempted": False, "repaired_scenes": []},
        }
    flag = episode.get("narration_preflight") or {}
    if flag.get("eligible") is False and flag.get("narration_key") == key:
        return {
            "eligible": False, "state": "return-to-story", "cached": True, "episode_id": episode.get("id"),
            "checks": [], "reasons": flag.get("reasons") or ["timing-failed"],
        }
    return None


def preflight(root=ROOT, write_timeline=False):
    reports = []
    # One episode that currently fails a content-policy check must not stop
    # this preflight from measuring every other ready storyboard's timing --
    # see brain/creator_series.py's episodes(skip_invalid=True) docstring.
    for episode in CreatorSeriesRegistry(root).episodes(skip_invalid=True):
        if episode.get("status") != "storyboard-ready-needs-assets":
            continue
        cached = _cached_report(episode)
        if cached:
            reports.append(cached)
            continue
        report = NarrationPreflight.repair_episode_timing(episode)
        reports.append(report)
        if write_timeline and not report.get("eligible"):
            # Found 2026-10-03: one storyboard with an unfittable 82-word
            # beat failed this whole step, so image production stopped for
            # every other ready storyboard for two days. Flag only the
            # failing episode -- CreatorSceneProduction skips a flagged
            # episode -- and let the rest proceed.
            _flag_blocked(root, episode, report)
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
                "narration_key": narration_key(episode),
            }
            payload.pop("narration_preflight", None)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blocked = [report.get("episode_id") for report in reports if not report.get("eligible")]
    return {
        "stage": "narration-preflight-complete", "eligible": not blocked,
        "reports": reports, "blocked": blocked,
        "ready_for_images": [report.get("episode_id") for report in reports if report.get("eligible")],
    }


def blocks_everything(result):
    """True only when storyboards are blocked and none can start images."""
    return bool(result["blocked"] and not result["ready_for_images"])


def _flag_blocked(root, episode, report):
    """Persist why this storyboard cannot start image production yet.

    Deterministic content only (no timestamp), so an unchanged failure does
    not rewrite -- and commit -- the file on every hourly run.
    """
    path = Path(root) / str(episode["file"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    flag = {
        "eligible": False, "reasons": report.get("reasons") or ["timing-failed"],
        "narration_key": narration_key(episode),
    }
    if payload.get("narration_preflight") == flag:
        return
    payload["narration_preflight"] = flag
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-eligible", action="store_true")
    parser.add_argument("--write-timeline", action="store_true",
                        help="Persist the measured per-scene visual holds before image production.")
    args = parser.parse_args()
    result = preflight(write_timeline=args.write_timeline)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    for report in result["reports"]:
        if not report.get("eligible"):
            reasons = ", ".join((report.get("reasons") or ["timing-failed"])[:3])
            print(f"::warning::storyboard {report.get('episode_id')} returned to Story: {reasons}", file=sys.stderr)
    # Fail loudly only when nothing can proceed to image production; an
    # individual blocked storyboard is flagged and skipped (see above).
    if args.require_eligible and blocks_everything(result):
        raise SystemExit("creator-narration-preflight-failed")
