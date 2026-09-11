import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.content_experiment import ContentExperimentExecutor
from brain.memory import MemoryEngine
if __name__ == "__main__":
    print(json.dumps(ContentExperimentExecutor(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))).evaluate_once(), ensure_ascii=False))
