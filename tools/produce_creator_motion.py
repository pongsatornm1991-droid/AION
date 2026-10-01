"""Create automatic Veo motion sources for one fully illustrated episode."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Windows only: subprocess.run() on a console app (ffmpeg.exe) briefly
# flashes a new, empty console window per call unless told not to -- the
# same class of bug already found and fixed in tools/sync_memory_from_
# github.py, brain/video_quality.py, and tools/reel_render.py. This module
# has its own `if __name__ == "__main__":` CLI entry point below, so it can
# run directly on the owner's Windows machine, not only from CI. Found by
# a follow-up audit (2026-09-22), not yet reported as an observed symptom.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_scene_production import CreatorSceneProduction
from brain.creator_series import CreatorSeriesRegistry
from tools.gemini_video import generate_scene_video, readiness


def _ffmpeg():
    """Return an available renderer without requiring a system package."""
    return shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def render_static_fallback(source_image, destination, *, aspect_ratio="9:16", seconds=5):
    """Create a new, auditable still-hold clip from the approved scene image.

    This is a resilience path, not a hidden replacement: it uses only the
    current episode's newly generated image and creates a measured MP4 that
    holds it still for the beat's exact duration. It keeps the release
    pipeline autonomous when an external image-to-video provider rejects or
    times out on a scene.

    Deliberately no zoom/pan: an earlier version applied the same gentle
    zoompan to every fallback scene, and because every scene's motion
    provider call failed on a real episode (Veo access, not this code, was
    the cause), all 13 scenes used it back to back. Cutting between clips
    that each reset to the same zoom start every ~5 seconds read as a
    repetitive, mechanical "jerk" at every cut rather than a real technical
    fault -- the owner asked for a still hold instead once shown the cause
    (2026-09-25).
    """
    source, target = Path(source_image), Path(destination)
    if not source.is_file():
        return False
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    target.parent.mkdir(parents=True, exist_ok=True)
    filtergraph = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},format=yuv420p"
    )
    try:
        subprocess.run(
            [_ffmpeg(), "-y", "-loop", "1", "-i", str(source), "-vf", filtergraph,
             "-t", str(seconds), "-r", "30", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(target)],
            check=True, capture_output=True, text=True, creationflags=_NO_WINDOW,
        )
        return target.is_file() and target.stat().st_size > 0
    except (OSError, subprocess.SubprocessError, RuntimeError):
        return False


def _episode(root, episode_id=None):
    # A quarantined invalid storyboard must not prevent a separate completed
    # episode from receiving its motion assets.  Scene production uses the
    # same safe registry mode; motion is the next production handoff.
    for item in CreatorSeriesRegistry(root).episodes(skip_invalid=True):
        if episode_id and item.get("id") != episode_id:
            continue
        if item.get("status") == "assets-ready-for-assembly":
            return item
    return None


def produce_once(root=ROOT, episode_id=None):
    root = Path(root)
    config = readiness()
    episode = _episode(root, episode_id)
    if episode is None:
        return {"stage": "no-asset-complete-episode", "provider": config["provider"]}
    motion_dir = root / "assets" / "content-library" / "aion-stories" / episode["id"] / "motion"
    created, failed = [], []
    aspect = "9:16" if episode.get("format") == "illustrated-narrated-short" else "16:9"
    producer = CreatorSceneProduction(root)
    for scene in episode.get("scenes") or []:
        target = motion_dir / f"{int(scene['n']):02d}.mp4"
        if target.is_file() and target.stat().st_size:
            scene["motion_path"] = str(target.relative_to(root)).replace("\\", "/")
            continue
        report = generate_scene_video(
            producer._prompt(episode, scene), root / str(scene.get("image") or ""), target,
            aspect_ratio=aspect,
        )
        fallback = False
        if not report.get("ok"):
            # Never substitute an old Reel. Produce a new still-hold clip from
            # this exact approved image so the release can continue, while
            # retaining the provider failure as transparent provenance.
            fallback = render_static_fallback(
                root / str(scene.get("image") or ""), target, aspect_ratio=aspect
            )
            if not fallback:
                failed.append({"scene": scene.get("n"), "state": report.get("state"),
                               "error_type": report.get("error_type")})
                break
        scene["motion_path"] = str(target.relative_to(root)).replace("\\", "/")
        scene["motion_contract"] = {
            "provider": "aion-static-fallback" if fallback else config["provider"],
            "model": "ffmpeg-still-hold-v1" if fallback else config["model"],
            "source_image": scene.get("image"), "mode": config["mode"],
            "fallback_reason": report.get("state") if fallback else None,
            # error_type alone (an exception class name, never a message) is
            # already secret-free -- persisting it is what let a real,
            # 13-for-13 Veo failure on a published episode be diagnosed
            # after the fact instead of only ever being visible in a report
            # dict that was never written to disk once the fallback quietly
            # succeeded (found 2026-09-25 investigating a jerky-motion report).
            "fallback_error_type": report.get("error_type") if fallback else None,
        }
        created.append(scene.get("n"))
    if created:
        source = root / episode["file"]
        source.write_text(json.dumps({key: value for key, value in episode.items() if key != "file"},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    completed = all(str(scene.get("motion_path") or "") and
                    (root / str(scene.get("motion_path"))).is_file()
                    for scene in episode.get("scenes") or [])
    return {"stage": "motion-assets-complete" if completed else "motion-assets-produced" if created else "motion-production-failed",
            "episode_id": episode["id"], "created": created, "failed": failed,
            "provider": config["provider"], "model": config["model"],
            "provider_configured": config["configured"]}


def produce_batch(root=ROOT, limit=5):
    """Finish motion for several ready episodes in one bounded worker shift.

    GitHub Actions commits made with its bot token do not reliably trigger a
    second workflow run.  Processing just one ready storyboard therefore made
    later episodes wait for the daily recovery cron even though their images
    were already complete.  Keep each episode's own provider/fallback record,
    but drain a small, deterministic batch in the same run.
    """
    root = Path(root)
    limit = max(1, int(limit))
    candidates = [
        str(item.get("id")) for item in CreatorSeriesRegistry(root).episodes(skip_invalid=True)
        if item.get("status") == "assets-ready-for-assembly" and item.get("id")
    ][:limit]
    reports = [produce_once(root, episode_id=episode_id) for episode_id in candidates]
    completed = [item.get("episode_id") for item in reports if item.get("stage") == "motion-assets-complete"]
    return {
        "stage": "motion-batch-complete" if reports else "no-asset-complete-episode",
        "requested_limit": limit,
        "episode_ids": candidates,
        "completed_episode_ids": completed,
        "reports": reports,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id")
    parser.add_argument("--limit", type=int, default=1,
                        help="Complete up to this many ready episodes in one bounded shift.")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = produce_once(episode_id=args.episode_id) if args.episode_id else produce_batch(limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    completed = (
        report.get("stage") == "motion-assets-complete" or
        report.get("stage") == "no-asset-complete-episode" or
        report.get("stage") == "motion-batch-complete" and all(
            item.get("stage") == "motion-assets-complete" for item in report.get("reports") or []
        )
    )
    if args.require_complete and not completed:
        raise SystemExit("creator-motion-production-failed")
