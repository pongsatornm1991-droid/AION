"""Capture public outcome signals for AION's published YouTube videos."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.youtube_audience import YouTubeAudienceCycle


if __name__ == "__main__":
    report = YouTubeAudienceCycle(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))).capture_once()
    print(json.dumps(report, ensure_ascii=False, indent=2))
