"""Run one read-only AION YouTube discovery turn."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.youtube_learning import YouTubeLearningCycle

if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(YouTubeLearningCycle(memory).discover_once(), ensure_ascii=False, indent=2))
