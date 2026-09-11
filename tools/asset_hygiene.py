"""Print a safe inventory of AION-generated media that may be archived later.

This command never moves or deletes a file.  Files marked ``review`` are
unreferenced and older than the retention window; a human can inspect them
before choosing a recoverable archive/quarantine action.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.asset_hygiene import AssetHygiene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--memory-root", default=os.getenv("AION_MEMORY_ROOT", str(ROOT / "memory")))
    parser.add_argument("--quarantine", action="store_true", help="Move only old unreferenced review files into content/quarantine; never deletes.")
    args = parser.parse_args()
    hygiene = AssetHygiene(ROOT, args.memory_root, args.retention_days)
    report = hygiene.quarantine_review_files() if args.quarantine else hygiene.scan()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
