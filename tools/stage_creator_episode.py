"""Stage up to a bounded batch of research-grounded Creator Studio storyboards.

2026-09-22: was a single stage_once() call, so even with the three-hourly
schedule a backlog of already-qualified handoffs could pile up -- see
StoryEpisodeStager.stage_batch()'s docstring and docs/ai-session-log.md
for why this changed to a small bounded batch instead of one at a time.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.story_episode_stager import StoryEpisodeStager
from main import build_provider


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["short", "long-form"], default="short")
    parser.add_argument("--limit", type=int, default=5,
                         help="Stage at most this many qualified handoffs in one shift.")
    args = parser.parse_args()
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    try:
        provider = build_provider()
    except Exception:
        provider = None
    report = StoryEpisodeStager(memory, ROOT, provider=provider).stage_batch(limit=args.limit, episode_format=args.format)
    print(json.dumps(report, ensure_ascii=False, indent=2))
