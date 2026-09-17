"""Reconcile an owner-confirmed YouTube publication with AION Studio."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.youtube_creator_queue import YouTubeCreatorQueue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-confirmed", action="store_true", help="Required safety acknowledgement.")
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--memory-root", default=os.getenv("AION_MEMORY_ROOT", str(ROOT / "aion-memory-data-sync")))
    args = parser.parse_args()
    if not args.owner_confirmed:
        parser.error("--owner-confirmed is required; this tool records only an owner-confirmed publication.")
    result = YouTubeCreatorQueue(MemoryEngine(args.memory_root), ROOT).reconcile_owner_confirmed_publication(
        args.episode_id, args.video_id, args.url
    )
    print(f"{result['stage']}: {result['episode_id']} -> {result['youtube']['url']}")


if __name__ == "__main__":
    main()
