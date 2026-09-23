"""One factual source for public channel identity and release policy."""

import json
from pathlib import Path


class ChannelPolicy:
    """Read the small versioned policy without granting any external access."""

    DEFAULTS = {
        "brand": {"channel_name": "Wait, How?", "handle": "@waithow-aion", "youtube_url": "https://www.youtube.com/@waithow-aion", "tagline": "Big questions. Clear visual stories.", "guide_name": "AION"},
        "publishing": {"timezone": "Asia/Bangkok", "shorts_days": list(range(7)), "shorts_time": "20:30", "shorts_buffer_target": 7, "readiness_horizon_hours": 168, "shorts_first": True},
        "production": {"automatic_release_visual_style": "aion-neon-diorama-3d-v1", "minimum_short_seconds": 50, "minimum_short_scenes": 10, "scene_seconds": 5},
    }

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def load(self):
        value = {section: dict(entries) for section, entries in self.DEFAULTS.items()}
        try:
            supplied = json.loads((self.root / "core" / "channel_policy.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return value
        for section, defaults in value.items():
            if isinstance(supplied.get(section), dict):
                defaults.update(supplied[section])
        return value

    def brand(self):
        return self.load()["brand"]

    def publishing(self):
        return self.load()["publishing"]

    def production(self):
        return self.load()["production"]
