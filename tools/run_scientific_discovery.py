import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from brain.memory import MemoryEngine
from brain.scientific_discovery import ScientificDiscoveryLab
print(json.dumps(ScientificDiscoveryLab(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))).propose_once(), ensure_ascii=False))
