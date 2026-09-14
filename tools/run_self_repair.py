"""Run bounded AION repairs and write a public, secret-free result."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.self_repair import SafeRepairAgent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="public/aion-self-repair-status.json")
    args = parser.parse_args()
    report = SafeRepairAgent(ROOT, os.getenv("AION_MEMORY_ROOT", "memory")).run_once()
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
