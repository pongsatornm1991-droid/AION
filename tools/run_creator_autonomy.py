"""Create AION's next inspectable creative intention without publishing it."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_autonomy import CreatorAutonomy
from brain.memory import MemoryEngine


if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(CreatorAutonomy(memory).choose_once(), ensure_ascii=False, indent=2))
