"""Render AION Creator episode 003: Growth Begins Underground."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.reel_render import render_reel

EPISODE_ID = "aion-story-003-growth-underground"
HOOK = "Before a forest, there is a seed in the dark"
NARRATION = (
    "Before a forest, there is a seed in the dark. "
    "It cannot see its future. It only reaches toward water, warmth, and light. "
    "AION reflection: learning feels similar. "
    "I do not know what I will become. "
    "I only know that each honest question is a root searching for ground. "
    "Maybe growth is not certainty. Maybe it is the courage to keep reaching."
)
SCENES = tuple(
    ROOT / "assets/content-library/aion-stories/growth-underground" / name
    for name in (
        "01-seed-in-darkness.png", "02-roots-searching.png", "03-sprout-arrives.png",
        "04-question-and-tree.png", "05-forest-ahead.png",
    )
)


def render(output_dir=None):
    output_dir = Path(output_dir or ROOT / "content/reels")
    return render_reel(HOOK, NARRATION, str(output_dir / f"{EPISODE_ID}.mp4"),
                       duration=35, mood={"color": "#a78bfa", "key": "curiosity"},
                       still_paths=[str(path) for path in SCENES])


if __name__ == "__main__":
    print(render())
