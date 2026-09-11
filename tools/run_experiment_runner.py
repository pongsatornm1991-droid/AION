import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.experiment_runner import ExperimentRunner
from brain.memory import MemoryEngine
if __name__ == "__main__":
    print(json.dumps(ExperimentRunner(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))).queue_once(), ensure_ascii=False))
