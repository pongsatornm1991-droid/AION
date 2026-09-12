"""Run AION's read-only engineering health inspection."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from brain.system_reliability import SystemReliability


def main():
    print(json.dumps(SystemReliability().snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
