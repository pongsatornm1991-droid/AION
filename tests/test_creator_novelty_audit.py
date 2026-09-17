import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_novelty_audit import CreatorNoveltyAudit
from brain.memory import MemoryEngine


class CreatorNoveltyAuditTests(unittest.TestCase):
    def test_retires_an_unfinished_storyboard_when_a_matching_public_episode_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            series = root / "content" / "creator_series"
            series.mkdir(parents=True)
            (series / "duplicate.json").write_text(json.dumps({
                "id": "duplicate", "title": "How an octopus changes color",
                "topic_key": "octopus chromatophores colour change mechanism",
                "status": "storyboard-ready-needs-assets",
                "sources": [{"url": "https://example.test/octopus"}],
            }), encoding="utf-8")
            memory = MemoryEngine(root / "memory")
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "published-octopus", "title": "How an Octopus Changes Color in Seconds",
                "topic_key": "octopus chromatophores colour change mechanism",
                "source_urls": ["https://example.test/octopus"],
                "youtube": {"video_id": "published", "privacy_status": "public"},
            }), memory_type="action")
            report = CreatorNoveltyAudit(memory, root).audit()
            self.assertEqual("duplicate-storyboards-retired", report["stage"])
            updated = json.loads((series / "duplicate.json").read_text(encoding="utf-8"))
            self.assertEqual("retired-do-not-publish", updated["status"])
            self.assertEqual("duplicate-topic-company-wide", updated["retirement_reason"])

    def test_keeps_a_distinct_storyboard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            series = root / "content" / "creator_series"
            series.mkdir(parents=True)
            (series / "new.json").write_text(json.dumps({
                "id": "new", "title": "Why do leaves change color?",
                "topic_key": "leaf pigments autumn color",
                "status": "storyboard-ready-needs-assets",
                "sources": [{"url": "https://example.test/leaves"}],
            }), encoding="utf-8")
            report = CreatorNoveltyAudit(MemoryEngine(root / "memory"), root).audit()
            self.assertEqual("no-duplicate-storyboards", report["stage"])
            updated = json.loads((series / "new.json").read_text(encoding="utf-8"))
            self.assertEqual("storyboard-ready-needs-assets", updated["status"])
