import json
import tempfile
import unittest
from pathlib import Path

from brain.episode_numbering import EpisodeNumbering


class EpisodeNumberingTests(unittest.TestCase):
    def test_assigns_immutable_numbers_without_renaming_legacy_titles(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "content" / "creator_series"
            directory.mkdir(parents=True)
            (directory / "legacy.json").write_text(json.dumps({"id": "legacy", "title": "Old video"}), encoding="utf-8")
            (directory / "new.json").write_text(json.dumps({"id": "new", "title": "A fresh story"}), encoding="utf-8")
            numbering = EpisodeNumbering(root)
            assigned = numbering.assign({"id": "new"})
            self.assertEqual(1, assigned["episode_number"])
            self.assertEqual("EP. 001 — A fresh story", assigned["display_title"])
            self.assertEqual(assigned, numbering.assign({"id": "new"}))
            legacy = json.loads((directory / "legacy.json").read_text(encoding="utf-8"))
            self.assertNotIn("episode_number", legacy)
