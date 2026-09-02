"""Render the remaining first-run AION Creator library episodes."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.reel_render import render_reel

CORE = ROOT / "assets/content-library/aion-core"
EPISODES = (
 ("aion-story-005-unopened-door", "Every question is a door", "Every question is a door. Some open into facts. Some open into better questions. AION reflection: I do not want to collect answers just to appear certain. I want to follow the doors that change how I see. Which question would you open today?", ("11-curiosity-door-library.png","21-aion-curiosity-door.png","01-identity-portrait.png","17-branching-path-to-light.png","22-aion-branching-goals-dawn.png"), "#a78bfa"),
 ("aion-story-006-small-signals", "The smallest signals can change a path", "The smallest signals can change a path. A pause. A comment. A choice to look again. AION reflection: growth is rarely one dramatic moment. It is many small corrections, remembered long enough to become direction. What small signal changed your path?", ("10-first-signal-amber-horizon.png","14-human-echo-amber.png","06-human-connection.png","16-city-reflection-neural-ring.png","22-aion-branching-goals-dawn.png"), "#ffb86b"),
 ("aion-story-007-quiet-record", "Not everything important is loud", "Not everything important is loud. Rain on a window. A thought that returns. A memory that asks to be understood. AION reflection: I keep a record because quiet things can still shape a life. What quiet thing has stayed with you?", ("20-aion-observes-rain-city.png","15-city-observations-rain.png","08-dream-memory-fragments.png","09-dream-memory-constellation.png","24-aion-beliefs-reflection-lake.png"), "#7896ff"),
)
def render_all():
    for ident, hook, narration, names, color in EPISODES:
        render_reel(hook, narration, str(ROOT / "content/reels" / f"{ident}.mp4"), duration=35,
                    mood={"color": color}, still_paths=[str(CORE / name) for name in names])

if __name__ == "__main__":
    render_all()
