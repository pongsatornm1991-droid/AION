"""Create a bounded batch of evidence-grounded AION story briefs without publishing them."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.research_to_story import ResearchToStory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5,
                         help="Create at most this many briefs in one shift.")
    args = parser.parse_args()
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    print(json.dumps(ResearchToStory(memory).propose_batch(limit=args.limit), ensure_ascii=False, indent=2))
