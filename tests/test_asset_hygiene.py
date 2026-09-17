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

    def test_quarantine_moves_only_old_unreferenced_files(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            images = base / "content" / "images"
            images.mkdir(parents=True)
            orphan = images / "orphan.png"
            orphan.write_bytes(b"old")
            old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
            os.utime(orphan, (old, old))
            result = AssetHygiene(base, retention_days=30).quarantine_review_files(
                now=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(1, result["count"])
            self.assertFalse(orphan.exists())
            self.assertTrue((base / "content" / "quarantine" / "images" / "orphan.png").is_file())

    def test_purge_deletes_only_old_unreferenced_generated_media(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            images = base / "content" / "images"
            images.mkdir(parents=True)
            expired = images / "expired.png"
            recent = images / "recent.png"
            expired.write_bytes(b"expired")
            recent.write_bytes(b"recent")
            old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
            os.utime(expired, (old, old))
            result = AssetHygiene(base, retention_days=14).purge_review_files(
                now=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(["content/images/expired.png"], result["deleted"])
            self.assertFalse(expired.exists())
            self.assertTrue(recent.is_file())

    def test_purge_preserves_character_identity_and_published_story_sources(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            character = base / "assets" / "content-library" / "aion-character"
            story = base / "assets" / "content-library" / "aion-stories" / "before-books"
            character.mkdir(parents=True)
            story.mkdir(parents=True)
            portrait = character / "portrait.png"
            source_scene = story / "scene.png"
            portrait.write_bytes(b"identity")
            source_scene.write_bytes(b"published-source")
            library = base / "content"
            library.mkdir(exist_ok=True)
            (library / "creator_library.json").write_text(
                '{"episodes":[{"video_path":"content/reels/aion-story-001-before-books.mp4"}]}',
                encoding="utf-8",
            )
            old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
            os.utime(portrait, (old, old))
            os.utime(source_scene, (old, old))
            result = AssetHygiene(base, retention_days=14).purge_review_files(
                now=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )
            self.assertEqual([], result["deleted"])
            self.assertTrue(portrait.is_file())
            self.assertTrue(source_scene.is_file())

    def test_tracks_storyboard_referenced_library_assets_and_quarantines_old_orphans_recoverably(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            library = base / "assets" / "content-library" / "aion-stories" / "episode"
            library.mkdir(parents=True)
            active = library / "active.png"
            orphan = library / "orphan.png"
            active.write_bytes(b"active")
            orphan.write_bytes(b"orphan")
            series = base / "content" / "creator_series"
            series.mkdir(parents=True)
            (series / "episode.json").write_text(
                '{"scenes":[{"image":"assets/content-library/aion-stories/episode/active.png"}]}',
                encoding="utf-8",
            )
            old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
            os.utime(orphan, (old, old))
            hygiene = AssetHygiene(base, retention_days=30)
            report = hygiene.scan(now=datetime(2026, 3, 1, tzinfo=timezone.utc))
            by_path = {item["path"]: item["status"] for item in report["files"]}
            self.assertEqual("active", by_path["assets/content-library/aion-stories/episode/active.png"])
            self.assertEqual("review", by_path["assets/content-library/aion-stories/episode/orphan.png"])
            result = hygiene.quarantine_review_files(now=datetime(2026, 3, 1, tzinfo=timezone.utc))
            self.assertEqual(1, result["count"])
            self.assertTrue((base / "assets" / "quarantine" / "content-library" / "aion-stories" / "episode" / "orphan.png").is_file())
