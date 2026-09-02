"""Render one asset-backed AION Creator episode from its registry entry."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain.creator_series import CreatorSeriesRegistry
from tools.reel_render import render_reel


def render_episode(episode_id, output=None):
    episode = next(
        (item for item in CreatorSeriesRegistry(ROOT).episodes() if item["id"] == episode_id),
        None,
    )
    if not episode:
        raise ValueError(f"Unknown creator episode: {episode_id}")
    stills = [ROOT / scene["image"] for scene in episode["scenes"] if scene.get("image")]
    if len(stills) != len(episode["scenes"]):
        raise ValueError(f"{episode_id} does not yet have an image for every scene.")
    narration = " ".join(scene["narration"] for scene in episode["scenes"])
    destination = Path(output) if output else ROOT / "content" / "reels" / f"{episode_id}.mp4"
    render_reel(
        episode["title"], narration, str(destination),
        duration=episode["target_duration_seconds"],
        mood={"color": "#22d3ee"},
        still_paths=[str(path) for path in stills],
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_id")
    parser.add_argument("--output")
    args = parser.parse_args()
    print(render_episode(args.episode_id, args.output))
