"""Detect drift between what's actually on YouTube and what the Creator
Studio memory queue has a record of.

Why this exists (2026-09-21): three real episodes were found published on
YouTube with no memory record at all (the queue never learned they went
public), discovered only because the owner happened to check YouTube Studio
and pasted the real URLs in chat. Left alone, a queue-less published episode
looks exactly like an unpublished one to the rest of Creator Studio, and can
be re-offered for upload -- a real duplicate-upload risk, caught only by
chance that day. This script checks for that same condition on a schedule
instead of waiting for someone to notice.

This is a DETECTOR, not a fixer. It never writes to memory and never calls
any YouTube write endpoint. A real hit still needs a human to confirm which
episode a video actually is (title alone is not always enough -- see the
2026-09-21 session log for a paste-order mismatch this same safeguard would
have caught) and then run `reconcile-youtube-creator` themselves, the same
one-video-at-a-time confirmation already required for that command.

Run with: python tools/check_youtube_publication_drift.py [--notify] [--limit 200]
Needs YOUTUBE_CLIENT_ID/YOUTUBE_CLIENT_SECRET/YOUTUBE_REFRESH_TOKEN and,
for --notify, TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID -- all already used by
other AION workflows, no new secret required.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.youtube_creator_queue import YouTubeCreatorQueue


def recorded_video_ids(memory):
    """episode_id already recorded for every video_id the Studio queue knows."""
    queue = YouTubeCreatorQueue(memory)
    by_video_id = {}
    for episode_id, (_entry, payload) in queue._records_by_episode().items():
        video_id = (payload.get("youtube") or {}).get("video_id")
        if video_id:
            by_video_id[video_id] = episode_id
    return by_video_id


def find_drift(memory, channel_videos):
    """Pure comparison: real channel videos vs the Studio's own records.

    Kept separate from any network call so it can be tested with plain
    fixture data instead of a real YouTube account.
    """
    recorded = recorded_video_ids(memory)
    orphaned = [video for video in channel_videos if video.get("video_id") not in recorded]
    return {
        "channel_video_count": len(channel_videos),
        "recorded_video_count": len(recorded),
        "orphaned_video_count": len(orphaned),
        "orphaned_videos": orphaned,
    }


def notify(orphaned_videos):
    """Best-effort Telegram alert. Never raises -- a notify failure must not
    make the detector itself look broken; the JSON report on stdout (and the
    workflow step summary) is still the source of truth either way."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    lines = [
        "AION: found YouTube video(s) with no Studio queue record.",
        "This is the exact condition that can cause a duplicate upload.",
        "Confirm each one is real (title + URL) before doing anything, then",
        "run reconcile-youtube-creator yourself -- never let anything auto-fix this.",
        "",
    ]
    for video in orphaned_videos[:10]:
        lines.append(
            f"- {video.get('title')} ({video.get('video_id')}) [{video.get('privacy_status')}]"
        )
    if len(orphaned_videos) > 10:
        lines.append(f"...and {len(orphaned_videos) - 10} more.")
    message = "\n".join(lines)
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data
        )
        urllib.request.urlopen(request, timeout=20)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200,
                        help="Most recent uploaded videos to check (default 200).")
    parser.add_argument("--notify", action="store_true",
                        help="Send a Telegram alert when drift is found.")
    args = parser.parse_args()

    from brain.thinker import Thinker
    from tools.youtube import list_uploaded_videos

    memory = Thinker().memory
    channel_videos = list_uploaded_videos(limit=args.limit)
    report = find_drift(memory, channel_videos)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["orphaned_videos"]:
        if args.notify:
            notify(report["orphaned_videos"])
        # A soft signal, not a hard CI failure: this mirrors release-
        # readiness.yml's own "early warning, never fails the build"
        # design. A human, not this script, decides what happens next.


if __name__ == "__main__":
    main()
