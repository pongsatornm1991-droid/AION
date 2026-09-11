"""Non-destructive asset inventory for AION-generated media."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


class AssetHygiene:
    """Classify generated media without deleting anything automatically."""

    MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v"}

    def __init__(self, root, memory_root=None, retention_days=30):
        self.root = Path(root)
        self.memory_root = Path(memory_root) if memory_root else self.root / "memory"
        self.retention_days = int(retention_days)

    def _references(self):
        """Find repo-relative media paths in private memory records only."""
        refs = set()
        if not self.memory_root.is_dir():
            return refs
        for record in self.memory_root.rglob("*.md"):
            try:
                text = record.read_text(encoding="utf-8")
            except OSError:
                continue
            refs.update(re.findall(r"content/(?:images|reels)/[^\s\"']+", text))
        return {item.rstrip(".,)]}") for item in refs}

    def scan(self, now=None):
        now = now or datetime.now(timezone.utc)
        references = self._references()
        cutoff = now - timedelta(days=self.retention_days)
        items = []
        for relative_dir in ("content/images", "content/reels"):
            directory = self.root / relative_dir
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in self.MEDIA_SUFFIXES:
                    continue
                relative = path.relative_to(self.root).as_posix()
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                referenced = relative in references
                status = "active" if referenced else ("review" if modified <= cutoff else "recent-unreferenced")
                items.append({
                    "path": relative, "bytes": path.stat().st_size,
                    "modified_at": modified.isoformat(), "referenced": referenced,
                    "status": status,
                })
        items.sort(key=lambda item: item["path"])
        return {
            "retention_days": self.retention_days,
            "files": items,
            "summary": {
                "active": sum(item["status"] == "active" for item in items),
                "recent_unreferenced": sum(item["status"] == "recent-unreferenced" for item in items),
                "review": sum(item["status"] == "review" for item in items),
                "review_bytes": sum(item["bytes"] for item in items if item["status"] == "review"),
            },
        }
