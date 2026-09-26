import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.thai_dub_cycle import ThaiDubCycle
from brain.memory import MemoryEngine
from main import build_provider, load_dotenv

if __name__ == "__main__":
    load_dotenv()
    cycle = ThaiDubCycle(
        MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory")),
        root=ROOT, provider=build_provider(),
    )
    report = cycle.dub_batch(limit=3)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
