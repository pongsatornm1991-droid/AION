"""Stage one research-grounded Creator Studio storyboard."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.story_episode_stager import StoryEpisodeStager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["short", "long-form"], default="short")
    args = parser.parse_args()
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(StoryEpisodeStager(memory, ROOT).stage_once(args.format), ensure_ascii=False, indent=2))
