"""Post Thai-audio versions of published Shorts to the Facebook Page.

    python tools/run_thai_facebook_crosspost.py --limit 1
    python tools/run_thai_facebook_crosspost.py --dry-run     # show what it would post
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.thai_facebook_crosspost import ThaiFacebookCrosspost
from brain.thinker import Thinker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=1, help="Maximum Thai Reels to post in this run (default: 1).")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be posted without rendering or posting.")
    args = parser.parse_args()

    crosspost = ThaiFacebookCrosspost(Thinker().memory, ROOT)
    report = crosspost.publish_batch(limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Nothing waiting is a normal state; only a real delivery failure is an error.
    if report.get("stage") == "failed":
        print(f"::warning title=thai-facebook-crosspost::{report['results'][-1].get('error')}"[:300])
        raise SystemExit("thai-facebook-crosspost-failed")


if __name__ == "__main__":
    main()
