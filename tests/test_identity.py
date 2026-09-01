"""Offline tests for brain/identity.py (Identity) -- there were no
tests for this loader before 2026-08-30, when the core/*.md files it
reads were found to have carried a formatting bug since the project's
first commits (see the audit doc) and a new "milestones" file was
added alongside the original four.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from brain.identity import Identity


class IdentityLoadTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.core_path = Path(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, filename, content):
        (self.core_path / filename).write_text(content, encoding="utf-8")

    def test_missing_directory_returns_empty_strings_not_an_error(self):
        identity = Identity(core_path=str(self.core_path / "does-not-exist"))
        loaded = identity.load()

        self.assertEqual(
            loaded,
            {
                "identity": "", "purpose": "", "values": "",
                "birth": "", "manifesto": "", "visual_identity": "", "curiosity_constitution": "", "roadmap": "", "milestones": "",
            },
        )

    def test_loads_each_real_file_verbatim(self):
        self._write("identity.md", "# AION Identity\n")
        self._write("purpose.md", "# AION Purpose\n")
        self._write("values.md", "# AION Values\n")
        self._write("birth.md", "# AION -- Birth Record\n")
        self._write("manifesto.md", "# AION Manifesto\n")
        self._write("visual_identity.md", "# AION Visual DNA\n")
        self._write("curiosity_constitution.md", "# Curiosity\n")
        self._write("aion_roadmap.md", "# Roadmap\n")
        self._write("milestones.md", "# AION Milestones\n")

        loaded = Identity(core_path=str(self.core_path)).load()

        self.assertEqual(loaded["identity"], "# AION Identity\n")
        self.assertEqual(loaded["purpose"], "# AION Purpose\n")
        self.assertEqual(loaded["values"], "# AION Values\n")
        self.assertEqual(loaded["birth"], "# AION -- Birth Record\n")
        self.assertEqual(loaded["manifesto"], "# AION Manifesto\n")
        self.assertEqual(loaded["visual_identity"], "# AION Visual DNA\n")
        self.assertEqual(loaded["curiosity_constitution"], "# Curiosity\n")
        self.assertEqual(loaded["roadmap"], "# Roadmap\n")
        self.assertEqual(loaded["milestones"], "# AION Milestones\n")

    def test_a_missing_individual_file_is_just_empty_not_fatal(self):
        # milestones.md is newer than the other four -- an older
        # checkout without it must not crash Identity.load().
        self._write("identity.md", "# AION Identity\n")

        loaded = Identity(core_path=str(self.core_path)).load()

        self.assertEqual(loaded["identity"], "# AION Identity\n")
        self.assertEqual(loaded["milestones"], "")

    def test_real_project_core_files_are_clean_of_the_2026_08_30_bug(self):
        # Regression guard for the backslash-escaping / CRLF bug that
        # sat in core/*.md since the project's first commits (fixed
        # 2026-08-30) -- fails loudly if it ever creeps back in.
        loaded = Identity().load()

        for name in ("identity", "purpose", "values", "birth", "manifesto", "visual_identity", "curiosity_constitution", "roadmap", "milestones"):
            text = loaded[name]
            self.assertNotIn("\r\n", text, f"{name}.md has CRLF line endings")
            for line in text.splitlines():
                self.assertFalse(
                    line.startswith(("\\#", "\\-")),
                    f"{name}.md has a stray backslash-escaped line: {line!r}",
                )


if __name__ == "__main__":
    unittest.main()
