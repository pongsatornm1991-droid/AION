import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.creator_reference_study import CreatorReferenceStudy
from brain.memory import MemoryEngine
from main import build_provider, load_dotenv

if __name__ == "__main__":
    load_dotenv()
    report = CreatorReferenceStudy(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory")), build_provider()).study_once()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
