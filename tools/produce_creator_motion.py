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


def render_kinetic_fallback(source_image, destination, *, aspect_ratio="9:16", seconds=5):
    """Create a new, auditable motion clip from the approved scene image.

    This is a resilience path, not a hidden replacement: it uses only the
    current episode's newly generated image and creates a measured MP4 with a
    gentle camera move. It keeps the release pipeline autonomous when an
    external image-to-video provider rejects or times out on a scene.
    """
    source, target = Path(source_image), Path(destination)
    if not source.is_file():
        return False
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Scale slightly larger than the output then move across that image. The
    # explicit duration means each visual still owns exactly one narration beat.
    zoom = "min(zoom+0.00045,1.08)"
    filtergraph = (
        f"scale={width * 12 // 10}:{height * 12 // 10}:force_original_aspect_ratio=increase,"
        f"crop={width * 12 // 10}:{height * 12 // 10},"
        f"zoompan=z='{zoom}':d={int(seconds) * 30}:s={width}x{height}:fps=30,format=yuv420p"
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
    for item in CreatorSeriesRegistry(root).episodes():
        if episode_id and item.get("id") != episode_id:
            continue
        if item.get("status") == "assets-ready-for-assembly":
            return item
    return None


def produce_once(root=ROOT, episode_id=None):
    root = Path(root)
    config = readiness()
    if not config["configured"]:
        return {"stage": "waiting-for-gemini-video-key", "provider": config["provider"]}
    episode = _episode(root, episode_id)
    if episode is None:
        return {"stage": "no-asset-complete-episode"}
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
            # Never substitute an old Reel. Produce a new kinetic clip from
            # this exact approved image so the release can continue, while
            # retaining the provider failure as transparent provenance.
            fallback = render_kinetic_fallback(
                root / str(scene.get("image") or ""), target, aspect_ratio=aspect
            )
            if not fallback:
                failed.append({"scene": scene.get("n"), "state": report.get("state"),
                               "error_type": report.get("error_type")})
                break
        scene["motion_path"] = str(target.relative_to(root)).replace("\\", "/")
        scene["motion_contract"] = {
            "provider": "aion-kinetic-fallback" if fallback else config["provider"],
            "model": "ffmpeg-pan-zoom-v1" if fallback else config["model"],
            "source_image": scene.get("image"), "mode": config["mode"],
            "fallback_reason": report.get("state") if fallback else None,
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
            "provider": config["provider"], "model": config["model"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = produce_once(episode_id=args.episode_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.require_complete and report.get("stage") not in {"motion-assets-complete", "no-asset-complete-episode"}:
        raise SystemExit("creator-motion-production-failed")
