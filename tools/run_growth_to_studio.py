import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.growth_to_studio import GrowthToStudio
from brain.memory import MemoryEngine
print(json.dumps(GrowthToStudio(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))).reflect_once(), ensure_ascii=False))
