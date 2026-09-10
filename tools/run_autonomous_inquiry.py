"""Run one audience-independent inquiry renewal for AION."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.autonomous_inquiry import AutonomousInquiryCycle
from brain.evaluator import OutputEvaluator
from brain.memory import MemoryEngine
from main import build_provider, load_dotenv


if __name__ == "__main__":
    load_dotenv()
    cycle = AutonomousInquiryCycle(
        MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory")), build_provider(), OutputEvaluator(),
    )
    print(json.dumps(cycle.run_once(), ensure_ascii=False, indent=2, default=str))
