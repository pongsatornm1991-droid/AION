"""Remove unfinished duplicate subjects from the AION Studio production queue."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_novelty_audit import CreatorNoveltyAudit
from brain.memory import MemoryEngine


if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(CreatorNoveltyAudit(memory, ROOT).audit(), ensure_ascii=False, indent=2))
