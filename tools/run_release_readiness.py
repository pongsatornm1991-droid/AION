"""Write AION's release-buffer status without publishing anything."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from brain.memory import MemoryEngine
from brain.release_readiness import ReleaseReadiness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="public/aion-release-readiness.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = ReleaseReadiness(MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory")), ROOT).snapshot()
    path = ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if args.strict and report["state"] != "ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
