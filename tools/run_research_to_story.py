"""Create one evidence-grounded AION story brief without publishing it."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.research_to_story import ResearchToStory


if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(ResearchToStory(memory).propose_once(), ensure_ascii=False, indent=2))
