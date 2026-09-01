import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from brain.evolution import EvolutionEngine
from brain.memory import MemoryEngine


class EvolutionEngineTests(unittest.TestCase):
    def test_records_evidence_backed_proposals_and_respects_weekly_cooldown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "VIDEO_LIBRARY.json"
            library.write_text(json.dumps({"videos": []}), encoding="utf-8")
            memory = MemoryEngine(root / "memory")
            engine = EvolutionEngine(memory, video_library_path=library)

            first = engine.propose_once(now=datetime(2026, 9, 1, 8, 0, 0), force=True)
            self.assertEqual(first["stage"], "proposed")
            self.assertTrue(first["recorded"])
            self.assertTrue(any(item["area"] == "creative-library" for item in first["proposals"]))
            stored = memory.all("evolution_proposals")
            self.assertEqual(len(stored), 1)
            self.assertIn("AION Evolution Proposal", stored[0]["content"])

            second = engine.propose_once(now=datetime(2026, 9, 2, 8, 0, 0))
            self.assertEqual(second["stage"], "not-due")


if __name__ == "__main__":
    unittest.main()
