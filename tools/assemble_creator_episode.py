"""Assemble one fully illustrated AION episode into a reviewable MP4.

This production handoff only reads an episode whose scene assets are complete,
renders a local MP4, and records the result.  Quality Gate and publishing
remain separate steps.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_series import CreatorSeriesRegistry
from brain.visual_story_policy import VisualStoryPolicy
from tools.reel_render import REEL_SIZE, WIDESCREEN_SIZE, render_reel


def _eligible_episode(root, episode_id=None):
    return next((episode for episode in CreatorSeriesRegistry(root).episodes()
                 if episode.get("status") == "assets-ready-for-assembly"
                 and (not episode_id or episode.get("id") == episode_id)), None)


def _timestamp(seconds):
    return f"{seconds // 3600:02}:{(seconds % 3600) // 60:02}:{seconds % 60:02},000"


def _write_subtitles(episode, output):
    """Create an inspectable SRT track from the approved storyboard narration."""
    seconds = int(episode["scene_seconds"])
    blocks = []
    for index, scene in enumerate(episode.get("scenes") or [], 1):
        start = (index - 1) * seconds
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(start + seconds)}\n{str(scene.get('narration') or '').strip()}\n")
    subtitle = output.with_suffix(".srt")
    subtitle.write_text("\n".join(blocks), encoding="utf-8")
    return subtitle


def assemble_once(root=ROOT, episode_id=None, renderer=render_reel):
    """Render one asset-complete episode and advance only that episode."""
    root = Path(root)
    episode = _eligible_episode(root, episode_id)
    if episode is None:
        return {"stage": "no-asset-complete-episode"}
    scenes = episode.get("scenes") or []
    images = [root / str(scene.get("image") or "") for scene in scenes]
    if not images or any(not image.is_file() for image in images):
        return {"stage": "missing-scene-assets", "episode_id": episode["id"]}
    seconds = int(episode.get("scene_seconds") or 0)
    if seconds > VisualStoryPolicy.MAX_SCENE_SECONDS:
        return {"stage": "scene-pacing-policy-failed", "episode_id": episode["id"], "scene_seconds": seconds}
    output = root / "content" / "reels" / f"{episode['id']}.mp4"
    narration = " ".join(str(scene.get("narration") or "").strip() for scene in scenes)
    try:
        frame_size = REEL_SIZE if episode.get("format") == "illustrated-narrated-short" else WIDESCREEN_SIZE
        renderer(episode["wonder_hook"], narration, str(output),
                 duration=int(episode["target_duration_seconds"]),
                 still_paths=[str(image) for image in images],
                 max_scene_seconds=VisualStoryPolicy.MAX_SCENE_SECONDS,
                 frame_size=frame_size)
    except Exception as exc:
        return {"stage": "assembly-failed", "episode_id": episode["id"], "error": str(exc)}
    if not output.is_file() or output.stat().st_size == 0:
        return {"stage": "assembly-output-missing", "episode_id": episode["id"]}
    subtitle = _write_subtitles(episode, output)
    source = root / episode["file"]
    episode["status"] = "production-ready-assets-and-script"
    source.write_text(json.dumps({key: value for key, value in episode.items() if key != "file"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"stage": "episode-rendered-for-quality", "episode_id": episode["id"],
            "video_path": str(output.relative_to(root)).replace("\\", "/"),
            "subtitle_path": str(subtitle.relative_to(root)).replace("\\", "/"),
            "scene_count": len(scenes), "format": episode.get("format")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id")
    args = parser.parse_args()
    print(json.dumps(assemble_once(episode_id=args.episode_id), ensure_ascii=False, indent=2))
