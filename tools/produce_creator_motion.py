"""Create automatic Veo motion sources for one fully illustrated episode."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_scene_production import CreatorSceneProduction
from brain.creator_series import CreatorSeriesRegistry
from tools.gemini_video import generate_scene_video, readiness


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
        if not report.get("ok"):
            failed.append({"scene": scene.get("n"), "state": report.get("state"),
                           "error_type": report.get("error_type")})
            break
        scene["motion_path"] = str(target.relative_to(root)).replace("\\", "/")
        scene["motion_contract"] = {
            "provider": config["provider"], "model": config["model"],
            "source_image": scene.get("image"), "mode": config["mode"],
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
