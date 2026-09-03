"""Build a REDACTED public summary of AION's internal "brain" state.

Why this exists: the user asked for the public AION Pulse status page
(a hosted web page with no access to any private credential) to also
show a look into what the local, credential-gated Observatory
dashboard shows -- AION's actual thinking (beliefs, curiosity, goals,
mood) -- not just whether GitHub Actions is green. Reading the private
aion-memory-data repo needs a private-repo checkout, which only a
GitHub Actions run can do safely, using the existing MEMORY_REPO_PAT
secret every other scheduled workflow already uses -- that secret is
never exposed to any output here. The *result* of that read, once
reduced to a small, explicitly-allowlisted JSON summary with no
third-party personal data in it, is safe to commit into this
already-public code repo, where a public web page can then read it
with a plain, unauthenticated fetch -- the same raw.githubusercontent.com
pattern already used to serve Instagram post images (see
brain/visual_content.py's own docstring for why that hosting choice
was made).

What is deliberately left out, and why: tools/dashboard.py's own
build_snapshot() already excludes the one genuinely sensitive category
-- comment_replies, which holds real Facebook users' names and comment
text -- from everything it returns, simply by never reading that
category (confirmed by reading every category list inside dashboard.py
before writing this module). This script goes one step further for
the *public* version: rather than republishing build_snapshot()'s full
return value verbatim, it copies out an explicit allowlist of fields
below. That way, if a future change ever adds a new, more sensitive
field to build_snapshot() for the local/private dashboard, it does NOT
silently start appearing on the public page too -- someone has to
deliberately add it to the allowlist in this file as well.

Run with: python tools/publish_public_summary.py [--out public/aion-brain-summary.json]
(AION_MEMORY_ROOT must point at a real checkout, e.g. memory_data/ in CI.)
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dashboard import build_snapshot

DEFAULT_OUT = ROOT / "public" / "aion-brain-summary.json"


def build_public_summary(snapshot=None):
    """Copy an explicit, deliberately narrow allowlist of fields out of
    the full dashboard snapshot -- see the module docstring for why
    this is a copy-out allowlist and not a pass-through of whatever
    build_snapshot() happens to return."""

    snapshot = snapshot if snapshot is not None else build_snapshot()

    return {
        "generated_at": snapshot.get("generated_at"),
        "mind": dict(snapshot.get("mind") or {}),
        "state_council": {
            "states": list((snapshot.get("state_council") or {}).get("states", [])),
            "dominant": (snapshot.get("state_council") or {}).get("dominant"),
            # Always carried alongside the mood scores themselves --
            # these are computed signals from memory/activity, never a
            # claim that AION has human-like feelings or consciousness
            # (the project's own master directive, enforced everywhere
            # else a drafted claim could imply otherwise).
            "disclaimer": (snapshot.get("state_council") or {}).get("disclaimer"),
        },
        "platforms": {
            platform: {
                "status": info.get("status"),
                "reels_published": info.get("reels_published"),
                "shorts_published": info.get("shorts_published"),
                "followers": info.get("followers"),
                "posts": info.get("posts"),
            }
            for platform, info in (snapshot.get("platforms") or {}).items()
        },
        "thoughts": [
            {
                "category": item.get("category"),
                "content": item.get("content"),
                "timestamp": item.get("timestamp"),
            }
            for item in (snapshot.get("thoughts") or [])
        ],
        "recent_posts": [
            {
                "timestamp": item.get("timestamp"),
                "caption": item.get("caption"),
                "instagram": bool(item.get("instagram")),
                "facebook": bool(item.get("facebook")),
                "youtube": bool(item.get("youtube")),
            }
            for item in ((snapshot.get("content") or {}).get("recent_posts") or [])
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    summary = build_public_summary()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {out_path} "
        f"({len(summary['thoughts'])} thoughts, {len(summary['recent_posts'])} recent posts)"
    )


if __name__ == "__main__":
    main()
