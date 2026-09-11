import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from brain.asset_hygiene import AssetHygiene


class AssetHygieneTests(unittest.TestCase):
    def test_marks_referenced_files_active_and_old_orphans_for_review(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            images = base / "content" / "images"
            images.mkdir(parents=True)
            active = images / "active.png"
            orphan = images / "orphan.png"
            active.write_bytes(b"a")
            orphan.write_bytes(b"b")
            old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
            os.utime(orphan, (old, old))
            memory = base / "memory"
            memory.mkdir()
            (memory / "pending_reels.md").write_text("content/images/active.png", encoding="utf-8")
            report = AssetHygiene(base, memory, retention_days=30).scan(
                now=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )
            by_path = {item["path"]: item["status"] for item in report["files"]}
            self.assertEqual("active", by_path["content/images/active.png"])
            self.assertEqual("review", by_path["content/images/orphan.png"])
