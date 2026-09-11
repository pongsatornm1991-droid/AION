"""Turn one new AION improvement proposal into a bounded internal experiment."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.improvement_review import ImprovementReview
from brain.memory import MemoryEngine

if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(ImprovementReview(memory).send_pending_once(), ensure_ascii=False, default=str))
