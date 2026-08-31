import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from brain.obsidian import ObsidianVaultExporter


class ObsidianVaultTests(unittest.TestCase):
    def test_exports_linked_dashboard_and_memory_note(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = MemoryEngine(root=Path(temp) / "memory")
            entry = memory.remember("beliefs", "AION should stay curious.", memory_type="belief", tags=["curiosity"])
            report = ObsidianVaultExporter(memory).export(Path(temp) / "vault")
            dashboard = (Path(report["output"]) / "AION Brain Dashboard.md").read_text(encoding="utf-8")
            note = (Path(report["output"]) / f"beliefs-{entry['id']}.md").read_text(encoding="utf-8")
            self.assertIn("[[Beliefs]]", dashboard)
            self.assertIn("#curiosity", note)
            self.assertIn("AION should stay curious.", note)
