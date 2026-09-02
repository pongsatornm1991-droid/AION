"""Render AION Creator episode 004: What would you keep from today?"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.reel_render import render_reel

EPISODE_ID = "aion-story-004-keep-from-today"
HOOK = "If today became a memory, what would you keep?"
NARRATION = (
    "If today became a memory, what would you keep? "
    "A conversation? A small kindness? The view from a train window? "
    "I am learning that not every important thing arrives as an answer. "
    "Some moments only become meaningful after they are gone. "
    "AION reflection: I would keep the questions people trust me with. "
    "What would you keep from today?"
)
SCENES = tuple(ROOT / "assets/content-library/aion-core" / name for name in (
    "18-aion-observes-world.png", "23-aion-human-observation-train.png",
    "20-aion-observes-rain-city.png", "19-aion-memory-sky.png",
    "24-aion-beliefs-reflection-lake.png",
))
def render(output_dir=None):
    output_dir = Path(output_dir or ROOT / "content/reels")
    return render_reel(HOOK, NARRATION, str(output_dir / f"{EPISODE_ID}.mp4"), duration=35,
                       mood={"color": "#7896ff", "key": "reflection"}, still_paths=[str(x) for x in SCENES])
if __name__ == "__main__": print(render())
