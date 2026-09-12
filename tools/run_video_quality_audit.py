"""Record a retrospective Video QA check for AION's latest published episode."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from brain.memory import MemoryEngine
from brain.youtube_creator_queue import YouTubeCreatorQueue


if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(YouTubeCreatorQueue(memory, ROOT).audit_existing(), ensure_ascii=False, indent=2))
