"""Publish a safe, read-only confirmation of the last delivery per platform."""

import argparse
import os
import sys
from pathlib import Path

# GitHub Actions invokes this file directly (``python tools/...``), which
# otherwise puts only tools/ on sys.path rather than the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.delivery_watchdog import dump
from brain.memory import MemoryEngine


def delivery_memory():
    """Use the workflow's synced private memory, never an empty local default."""
    return MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="public/aion-delivery-status.json")
    args = parser.parse_args()
    report = dump(delivery_memory(), args.out)
    print(f"Delivery watchdog: {report['summary']}")


if __name__ == "__main__":
    main()
