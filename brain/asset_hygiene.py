"""Evidence-based inventory and bounded cleanup for AION-generated media."""

import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


class AssetHygiene:
    """Classify media and purge only verified unreferenced generated files."""

    MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v"}
    MANAGED_DIRECTORIES = (
        "content/images",
        "content/reels",
        "assets/content-library/aion-stories",
        "assets/content-library/aion-character",
    )
    # These are early-warning limits, not permission to delete.  They make a
    # growing library visible before it can affect a workstation or CI clone.
    WARNING_BYTES = 1_500 * 1024 * 1024
    CRITICAL_BYTES = 3_000 * 1024 * 1024

    def __init__(self, root, memory_root=None, retention_days=30):
        self.root = Path(root)
        self.memory_root = Path(memory_root) if memory_root else self.root / "memory"
        self.retention_days = int(retention_days)

    def _references(self):
        """Find repo-relative media paths in memory and active storyboards."""
        refs = set()
        records = []
        if self.memory_root.is_dir():
            records.extend(self.memory_root.rglob("*.md"))
        storyboard_root = self.root / "content" / "creator_series"
        if storyboard_root.is_dir():
            records.extend(storyboard_root.glob("*.json"))
        creator_library = self.root / "content" / "creator_library.json"
        if creator_library.is_file():
            records.append(creator_library)
        pattern = (
            r"(?:content/(?:images|reels)/[^\s\"']+|"
            r"assets/content-library/(?:aion-stories|aion-character)/[^\s\"']+)"
        )
        for record in records:
            try:
                text = record.read_text(encoding="utf-8")
            except OSError:
                continue
            refs.update(re.findall(pattern, text))
        return {item.rstrip(".,)]}") for item in refs}

    def _protected_prefixes(self):
        """Return durable assets that must never be treated as production waste.

        Character references are the AION visual identity.  Source scenes for
        a published creator-library title are retained as the provenance of a
        public work, even if the current storyboard has since been retired.
        """
        prefixes = {"assets/content-library/aion-character/"}
        library_path = self.root / "content" / "creator_library.json"
        if not library_path.is_file():
            return prefixes
        try:
            payload = json.loads(library_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return prefixes
        entries = payload.get("episodes", []) if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            return prefixes
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            video_path = str(entry.get("video_path") or "")
            match = re.search(r"aion-story-\d+-(.+)\.mp4$", video_path)
            if match:
                prefixes.add(f"assets/content-library/aion-stories/{match.group(1)}/")
        return prefixes

    def scan(self, now=None):
        now = now or datetime.now(timezone.utc)
        references = self._references()
        protected_prefixes = self._protected_prefixes()
        cutoff = now - timedelta(days=self.retention_days)
        items = []
        for relative_dir in self.MANAGED_DIRECTORIES:
            directory = self.root / relative_dir
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in self.MEDIA_SUFFIXES:
                    continue
                relative = path.relative_to(self.root).as_posix()
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                referenced = relative in references
                protected = any(relative.startswith(prefix) for prefix in protected_prefixes)
                status = "protected" if protected else ("active" if referenced else ("review" if modified <= cutoff else "recent-unreferenced"))
                items.append({
                    "path": relative, "bytes": path.stat().st_size,
                    "modified_at": modified.isoformat(), "referenced": referenced, "protected": protected,
                    "status": status,
                })
        items.sort(key=lambda item: item["path"])
        managed_bytes = sum(item["bytes"] for item in items)
        storage_state = (
            "critical" if managed_bytes >= self.CRITICAL_BYTES else
            "warning" if managed_bytes >= self.WARNING_BYTES else "healthy"
        )
        return {
            "retention_days": self.retention_days,
            "files": items,
            "summary": {
                "total_files": len(items),
                "active": sum(item["status"] == "active" for item in items),
                "protected": sum(item["status"] == "protected" for item in items),
                "recent_unreferenced": sum(item["status"] == "recent-unreferenced" for item in items),
                "review": sum(item["status"] == "review" for item in items),
                "review_bytes": sum(item["bytes"] for item in items if item["status"] == "review"),
                "managed_bytes": managed_bytes,
                "storage_state": storage_state,
                "warning_bytes": self.WARNING_BYTES,
                "critical_bytes": self.CRITICAL_BYTES,
            },
        }

    def quarantine_review_files(self, now=None):
        """Recoverably move only confirmed old, unreferenced media.

        The destination stays inside the repository so Git retains the full
        history and a file can be restored with a normal move. Nothing is
        deleted, and files are re-scanned immediately before each move.
        """
        report = self.scan(now=now)
        moved = []
        for item in report["files"]:
            if item["status"] != "review":
                continue
            source = (self.root / item["path"]).resolve()
            root_content = (self.root / "content").resolve()
            root_assets = (self.root / "assets").resolve()
            if not source.is_file() or not (root_content in source.parents or root_assets in source.parents):
                continue
            if root_content in source.parents:
                relative = source.relative_to(root_content)
                destination = self.root / "content" / "quarantine" / relative
            else:
                relative = source.relative_to(root_assets)
                destination = self.root / "assets" / "quarantine" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                destination = destination.with_name(
                    f"{destination.stem}-{source.stat().st_mtime_ns}{destination.suffix}"
                )
            shutil.move(str(source), str(destination))
            moved.append({"from": item["path"], "to": destination.relative_to(self.root).as_posix()})
        return {"moved": moved, "count": len(moved), "scan": report["summary"]}

    def purge_review_files(self, now=None):
        """Delete only files that are both unreferenced and past retention.

        This intentionally does not inspect, delete, or rewrite source code,
        credentials, account data, memories, or any file outside the four
        generated-media directories.  The workflow commit is the audit trail;
        Git history retains a recoverable record of a removed tracked asset.
        """
        report = self.scan(now=now)
        deleted = []
        content_root = (self.root / "content").resolve()
        assets_root = (self.root / "assets").resolve()
        for item in report["files"]:
            if item["status"] != "review":
                continue
            source = (self.root / item["path"]).resolve()
            if not source.is_file() or not (content_root in source.parents or assets_root in source.parents):
                continue
            source.unlink()
            deleted.append(item["path"])
        return {"deleted": deleted, "count": len(deleted), "scan": report["summary"]}
