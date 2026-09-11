"""Record an operator-observed Facebook Group campaign status.

This is deliberately a local bookkeeping command. It does not publish,
approve, scrape, or reply on Facebook; AION uses it only after a status is
visibly confirmed in the group UI.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.community_campaign import CommunityCampaignRegistry


def main():
    parser = argparse.ArgumentParser(description="Record an observed community-campaign status")
    parser.add_argument("--id", required=True, help="campaign id from content/group_campaigns/registry.json")
    parser.add_argument("--status", required=True, choices=sorted(CommunityCampaignRegistry.VALID_STATUSES))
    parser.add_argument("--note", default="", help="brief observation, never a private message or commenter data")
    args = parser.parse_args()
    print(json.dumps(CommunityCampaignRegistry().transition(args.id, args.status, args.note), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
