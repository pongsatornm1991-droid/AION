"""Assemble one fully illustrated AION episode into a reviewable MP4.

This production handoff only reads an episode whose scene assets are complete,
renders a local MP4, and records the result.  Quality Gate and publishing
remain separate steps.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_series import CreatorSeriesRegistry
from brain.video_quality import VideoQualityGate
from brain.visual_story_policy import VisualStoryPolicy
from tools.reel_render import AudioTimingError, REEL_SIZE, WIDESCREEN_SIZE, render_reel


def _eligible_episode(root, episode_id=None):
    """Find a fresh episode, or repair a render that failed its real gate."""
    root = Path(root)
    candidates = []
    for episode in CreatorSeriesRegistry(root).episodes():
        if episode_id and episode.get("id") != episode_id:
            continue
        if episode.get("status") == "assets-ready-for-assembly":
            candidates.append((0, episode))
        elif episode.get("status") == "production-ready-assets-and-script":
            output = root / "content" / "reels" / f"{episode['id']}.mp4"
            kind = "short" if episode.get("format") == "illustrated-narrated-short" else "long-form"
            if not VideoQualityGate(root).assess(output, kind).get("eligible"):
                candidates.append((1, episode))
    # A corrective release is explicitly more urgent than unrelated repairs.
    # A malformed historical episode must never block the promised new slot.
    candidates.sort(key=lambda item: (
        (item[1].get("special_release") or {}).get("release_priority") != "urgent",
        item[0], item[1].get("id") or "",
    ))
    return candidates[0][1] if candidates else None


def _timestamp(seconds):
    milliseconds = round(float(seconds) * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def _write_subtitles(episode, output):
    """Create an inspectable SRT track from the approved storyboard narration."""
    seconds = int(episode["scene_seconds"])
    timing_file = output.with_suffix(".timing.json")
    try:
        durations = json.loads(timing_file.read_text(encoding="utf-8")).get("scene_durations") or []
    except (OSError, ValueError, TypeError):
        durations = []
    blocks = []
    start = 0
    for index, scene in enumerate(episode.get("scenes") or [], 1):
        scene_duration = float(durations[index - 1]) if len(durations) >= index else seconds
        end = start + scene_duration
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{str(scene.get('narration') or '').strip()}\n")
        start = end
    subtitle = output.with_suffix(".srt")
    subtitle.write_text("\n".join(blocks), encoding="utf-8")
    return subtitle


def backfill_subtitles_once(root=ROOT):
    """Restore a missing caption track without re-rendering a finished episode.

    A long-form upload is intentionally blocked without an inspectable SRT
    track.  This repair uses the already-approved narration in the storyboard;
    it never changes the video, calls a provider, or publishes anything.
    """
    root = Path(root)
    repaired = []
    for episode in CreatorSeriesRegistry(root).episodes():
        if episode.get("status") != "production-ready-assets-and-script":
            continue
        output = root / "content" / "reels" / f"{episode['id']}.mp4"
        subtitle = output.with_suffix(".srt")
        if output.is_file() and not subtitle.is_file():
            _write_subtitles(episode, output)
            repaired.append({
                "episode_id": episode["id"],
                "subtitle_path": str(subtitle.relative_to(root)).replace("\\", "/"),
            })
    return {"stage": "subtitle-backfill-complete", "repaired": repaired, "count": len(repaired)}


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
    motion = [root / str(scene.get("motion_path") or "") for scene in scenes]
    use_motion = bool(motion) and all(path.is_file() and path.stat().st_size for path in motion)
    motion_required = os.getenv("AION_REQUIRE_MOTION_VIDEO", "true").strip().lower() not in {"0", "false", "no"}
    if motion_required and not use_motion:
        # A completed still-image set is deliberately not a publishable video
        # under the Auto-video policy.  It stays visible in Studio until the
        # automatic provider has delivered every motion source.
        return {"stage": "waiting-for-automatic-motion", "episode_id": episode["id"],
                "completed_motion_scenes": sum(path.is_file() and path.stat().st_size for path in motion),
                "required_motion_scenes": len(scenes)}
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
                 motion_paths=[str(path) for path in motion] if use_motion else None,
                 max_scene_seconds=VisualStoryPolicy.MAX_RENDERED_SCENE_SECONDS,
                 frame_size=frame_size,
                 scene_narrations=[str(scene.get("narration") or "").strip() for scene in scenes])
    except AudioTimingError as exc:
        return {"stage": "audio-timing-failed", "episode_id": episode["id"], "error": str(exc)}
    except Exception as exc:
        return {"stage": "assembly-failed", "episode_id": episode["id"], "error": str(exc)}
    if not output.is_file() or output.stat().st_size == 0:
        return {"stage": "assembly-output-missing", "episode_id": episode["id"]}
    kind = "short" if episode.get("format") == "illustrated-narrated-short" else "long-form"
    quality = VideoQualityGate(root).assess(output, kind)
    if not quality.get("eligible"):
        return {"stage": "assembly-quality-failed", "episode_id": episode["id"], "quality": quality}
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
    parser.add_argument("--backfill-subtitles", action="store_true")
    parser.add_argument("--require-rendered", action="store_true",
                        help="Exit non-zero when final production fails; waiting for automatic motion is a valid handoff.")
    args = parser.parse_args()
    report = backfill_subtitles_once() if args.backfill_subtitles else assemble_once(episode_id=args.episode_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # A scheduled job may legitimately have no storyboard ready.  However,
    # once it starts on an asset-complete episode, any other result is a real
    # production failure and must be visible to downstream workflows.
    if args.require_rendered and report.get("stage") not in {
        "episode-rendered-for-quality", "no-asset-complete-episode",
        # Veo is intentionally a separate automatic worker.  Images may be
        # complete while it is creating the matching motion sources; that is
        # a visible handoff, not an assembly failure.
        "waiting-for-automatic-motion",
    }:
        raise SystemExit("creator-episode-assembly-failed")
