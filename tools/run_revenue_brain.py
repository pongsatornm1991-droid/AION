"""Record AION's next revenue-readiness proposal without any transaction."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Windows terminals can default to a legacy code page; the proposal contains
# Thai text and must remain runnable locally as well as in GitHub Actions.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from brain.memory import MemoryEngine
from brain.revenue_brain import RevenueBrain


if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(RevenueBrain(memory).propose_once(), ensure_ascii=False))
