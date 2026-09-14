"""Read-only evidence watchdog for AION's public publishing spine."""

import json
from datetime import datetime, timedelta, timezone

from brain.tools import ToolLifecycle
from brain.youtube_creator_queue import YouTubeCreatorQueue


class DeliveryWatchdog:
    """Reports recent confirmed deliveries without exposing account IDs or tokens."""

    PLATFORM_TOOLS = {
        "facebook": {"post_to_facebook", "post_photo_to_facebook", "post_reel_to_facebook"},
        "instagram": {"post_to_instagram", "post_reel_to_instagram"},
    }

    def __init__(self, memory, root=None, max_age_hours=30):
        self.memory = memory
        self.root = root
        self.max_age = timedelta(hours=max_age_hours)

    @staticmethod
    def _time(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None

    def _latest_actions(self):
        latest = {platform: None for platform in self.PLATFORM_TOOLS}
        for action in ToolLifecycle(self.memory).actions(status="executed"):
            for platform, names in self.PLATFORM_TOOLS.items():
                if action.get("tool") in names:
                    when = self._time(action.get("timestamp"))
                    if when and (latest[platform] is None or when > latest[platform]):
                        latest[platform] = when
        return latest

    def _latest_youtube(self):
        latest = None
        queue = YouTubeCreatorQueue(self.memory, root=self.root)
        for entry, payload in queue._records_by_episode().values():
            if (payload.get("youtube") or {}).get("video_id"):
                when = self._time(entry.get("timestamp"))
                if when and (latest is None or when > latest):
                    latest = when
        return latest

    def snapshot(self, now=None):
        now = now or datetime.now(timezone.utc)
        evidence = self._latest_actions()
        evidence["youtube"] = self._latest_youtube()
        platforms = []
        for platform in ("facebook", "instagram", "youtube"):
            when = evidence[platform]
            age = (now - when) if when else None
            state = "verified" if when and age <= self.max_age else "attention"
            platforms.append({
                "platform": platform,
                "state": state,
                "label": "ยืนยันการเผยแพร่แล้ว" if state == "verified" else "ยังไม่มีหลักฐานล่าสุด",
                "last_confirmed_at": when.isoformat() if when else None,
                "max_age_hours": int(self.max_age.total_seconds() // 3600),
            })
        return {
            "generated_at": now.isoformat(),
            "summary": "pass" if all(item["state"] == "verified" for item in platforms) else "attention",
            "platforms": platforms,
        }


def dump(memory, out_path, root=None):
    from pathlib import Path
    report = DeliveryWatchdog(memory, root=root).snapshot()
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
