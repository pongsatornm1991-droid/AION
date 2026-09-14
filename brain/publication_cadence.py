"""Coordinate AION feed cadence across independent publishing pipelines."""

from datetime import datetime
from zoneinfo import ZoneInfo

from brain.tools import ToolLifecycle


class PublicationCadence:
    """Allow only one confirmed feed item per platform per Bangkok day."""

    TIMEZONE = ZoneInfo("Asia/Bangkok")
    TOOLS = {
        "facebook": {"post_to_facebook", "post_photo_to_facebook", "post_reel_to_facebook"},
        "instagram": {"post_to_instagram", "post_reel_to_instagram"},
    }

    def __init__(self, memory):
        self.memory = memory

    @classmethod
    def _date(cls, value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(cls.TIMEZONE).date()
        except ValueError:
            return None

    def has_slot(self, platform, now=None):
        platform = str(platform or "").lower()
        if platform not in self.TOOLS:
            return True
        today = (now or datetime.now(self.TIMEZONE)).astimezone(self.TIMEZONE).date()
        for action in ToolLifecycle(self.memory).actions(status="executed"):
            if action.get("tool") in self.TOOLS[platform] and self._date(action.get("timestamp")) == today:
                return False
        return True
