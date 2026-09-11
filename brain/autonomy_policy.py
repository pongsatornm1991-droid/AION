"""Durable, inspectable boundaries for AION's operating authority."""

import json
from pathlib import Path


class AutonomyPolicy:
    """Read the project authority policy without ever storing credentials."""

    DEFAULT = {
        "public_publishing": {"enabled": False, "mode": "owner-confirmation-required"},
        "chair_approval_required": ["credentials", "account permissions", "money", "contracts"],
    }

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.data = self._load()

    def _load(self):
        path = self.root / "config" / "aion_authority.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return self.DEFAULT
        return value if isinstance(value, dict) else self.DEFAULT

    @property
    def public_publishing_enabled(self):
        return bool((self.data.get("public_publishing") or {}).get("enabled"))

    @property
    def publishing_mode(self):
        return (self.data.get("public_publishing") or {}).get("mode", "owner-confirmation-required")

    def public_publishing_summary(self):
        if not self.public_publishing_enabled:
            return "ยังต้องให้ประธานยืนยันก่อนเผยแพร่"
        return "AION เผยแพร่ผลงานสาธารณะได้เองหลังผ่าน Quality Gate"
