"""Inspect generated media and perform bounded cleanup only when requested.

Files marked ``review`` are unreferenced and older than the retention window.
The normal command is read-only.  ``--quarantine`` is recoverable; ``--purge``
is restricted to confirmed old, unreferenced generated media.
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
    parser.add_argument("--retention-days", type=int, default=14)
    parser.add_argument("--memory-root", default=os.getenv("AION_MEMORY_ROOT", str(ROOT / "memory")))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--quarantine", action="store_true", help="Move only old unreferenced review files into content/ or assets/quarantine; never deletes.")
    action.add_argument("--purge", action="store_true", help="Delete only old unreferenced generated media in the managed directories.")
    args = parser.parse_args()
    hygiene = AssetHygiene(ROOT, args.memory_root, args.retention_days)
    report = (
        hygiene.purge_review_files() if args.purge else
        hygiene.quarantine_review_files() if args.quarantine else
        hygiene.scan()
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
