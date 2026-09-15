import json
import tempfile
import unittest
from brain.growth_to_studio import GrowthToStudio
from brain.memory import MemoryEngine


class GrowthToStudioTests(unittest.TestCase):
    def test_waits_for_real_cross_content_evidence_then_creates_one_handoff(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            for number in range(3):
                memory.remember("content_attribution", json.dumps({"content_id": f"c{number}", "media_id": f"m{number}", "like_count": number, "comments_count": number}), "observation")
            report = GrowthToStudio(memory).reflect_once()
            self.assertEqual("handoff-created", report["stage"])
            self.assertIn("Story Architect", report["handoff"]["to"])
            self.assertEqual("unchanged", GrowthToStudio(memory).reflect_once()["stage"])
