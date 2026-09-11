import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_reference_study import CreatorReferenceStudy
from brain.memory import MemoryEngine


class Provider:
    def generate(self, prompt):
        return "1. Open with one visual question.\n2. Change the scene with each idea.\n3. End with an original AION reflection."


class CreatorReferenceStudyTests(unittest.TestCase):
    def test_studies_one_reference_as_original_craft_notes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "refs.json"
            path.write_text(json.dumps({"references": [{"id": "sample", "url": "https://www.youtube.com/watch?v=abc123"}]}), encoding="utf-8")
            memory = MemoryEngine(root)
            report = CreatorReferenceStudy(memory, Provider(), metadata_fn=lambda ids: [{"video_id": "abc123", "title": "A public title"}], reference_path=path).study_once()
            self.assertEqual("studied", report["stage"])
            record = json.loads(memory.all("creator_reference_studies")[0]["content"])
            self.assertIn("not a reconstruction", record["epistemic_status"])

    def test_missing_key_is_reported_without_a_record(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "refs.json"
            path.write_text(json.dumps({"references": [{"id": "sample", "url": "https://www.youtube.com/watch?v=abc123"}]}), encoding="utf-8")
            report = CreatorReferenceStudy(MemoryEngine(root), Provider(), metadata_fn=lambda ids: (_ for _ in ()).throw(RuntimeError("YOUTUBE_DATA_API_KEY is required")), reference_path=path).study_once()
            self.assertEqual("configuration-needed", report["stage"])
