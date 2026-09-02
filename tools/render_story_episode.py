"""Render the first source-grounded illustrated AION Creator episode.

This is deliberately a local rendering operation. Publishing remains a
separate lifecycle action, so a finished episode can be reviewed and queued
without silently posting it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# This script is invoked directly by the workflow (`python tools/...`), so
# explicitly retain the repository root for the renderer's package imports.
sys.path.insert(0, str(ROOT))
from tools.reel_render import render_reel
EPISODE_ID = "aion-story-001-before-books"
HOOK = "Before books, people left stories on stone"
NARRATION = (
    "Before books, people left stories on stone. "
    "In Sulawesi, Indonesia, a cave painting of a warty pig is dated to about "
    "forty-five thousand years ago. "
    "Across the world, cave artists marked hands, animals, and movement. "
    "We do not know every reason they made them. "
    "AION reflection: a handprint can be a small message across time. "
    "It says: someone was here. "
    "Perhaps every record begins not with an answer, but with a wish to be remembered."
)
SCENES = (
    ROOT / "assets/content-library/aion-stories/before-books/01-aion-enters-cave-v2.png",
    ROOT / "assets/content-library/aion-stories/before-books/02-cave-wall-warty-pig.png",
    ROOT / "assets/content-library/aion-stories/before-books/03-aion-handprint.png",
    ROOT / "assets/content-library/aion-stories/before-books/02-ancient-hand-stencil.png",
    ROOT / "assets/content-library/aion-stories/before-books/04-constellation-memory.png",
    ROOT / "assets/content-library/aion-illustrated/03-momentum-amber-horizon.png",
)


def render(output_dir=None):
    output_dir = Path(output_dir or ROOT / "content/reels")
    output = output_dir / f"{EPISODE_ID}.mp4"
    return render_reel(
        HOOK, NARRATION, str(output), duration=42,
        mood={"color": "#a78bfa", "key": "curiosity"},
        still_paths=[str(path) for path in SCENES],
    )


if __name__ == "__main__":
    print(render())
