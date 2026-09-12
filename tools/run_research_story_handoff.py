"""Create one auditable Story Agent handoff from a research-ready brief."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.research_story_handoff import ResearchStoryHandoff

if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(ResearchStoryHandoff(memory).create_once(), ensure_ascii=False, indent=2))
