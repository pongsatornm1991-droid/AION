"""Record AION's next event-aware cognitive focus."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.autonomic_drive import AutonomicDrive
from brain.memory import MemoryEngine

if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(AutonomicDrive(memory).decide_once(), ensure_ascii=False, indent=2))
