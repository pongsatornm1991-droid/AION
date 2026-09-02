"""Render AION Creator episode 002: a source-grounded story about light."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.reel_render import render_reel


EPISODE_ID = "aion-story-002-sunrise-message"
HOOK = "Every sunrise is a message from the past"
NARRATION = (
    "Every sunrise is a message from the past. "
    "Light from the Sun needs about eight minutes and twenty seconds to reach Earth. "
    "So the Sun you see is already eight minutes old. "
    "The farther a star is, the farther back in time its light began. "
    "AION reflection: perhaps attention works that way too. "
    "A moment arrives, and only then can we understand what it has carried."
)
SCENES = (
    ROOT / "assets/content-library/aion-stories/sunrise-message/01-rooftop-before-sunrise.png",
    ROOT / "assets/content-library/aion-stories/sunrise-message/02-sunlight-crosses-space.png",
    ROOT / "assets/content-library/aion-stories/sunrise-message/03-arriving-light.png",
    ROOT / "assets/content-library/aion-stories/sunrise-message/04-distant-light.png",
    ROOT / "assets/content-library/aion-stories/sunrise-message/05-walk-into-dawn.png",
)


def render(output_dir=None):
    output_dir = Path(output_dir or ROOT / "content/reels")
    return render_reel(
        HOOK,
        NARRATION,
        str(output_dir / f"{EPISODE_ID}.mp4"),
        duration=35,
        mood={"color": "#ffb86b", "key": "momentum"},
        still_paths=[str(path) for path in SCENES],
    )


if __name__ == "__main__":
    print(render())
