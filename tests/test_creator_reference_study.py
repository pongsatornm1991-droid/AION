import json
import tempfile
import unittest
from pathlib import Path

from brain.creator_reference_study import CreatorReferenceStudy
from brain.memory import MemoryEngine


class Provider:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
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

    def test_studies_the_small_reference_set_in_one_run(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "refs.json"
            path.write_text(json.dumps({"references": [
                {"id": "one", "url": "https://www.youtube.com/watch?v=one"},
                {"id": "two", "url": "https://www.youtube.com/watch?v=two"},
            ]}), encoding="utf-8")
            calls = []
            def metadata(ids):
                calls.append(ids)
                return [{"video_id": video_id, "title": video_id} for video_id in ids]
            memory = MemoryEngine(root)
            provider = Provider()
            report = CreatorReferenceStudy(memory, provider, metadata_fn=metadata, reference_path=path).study_all_pending()
            self.assertEqual("batch-complete", report["stage"])
            self.assertEqual(2, report["studied"])
            self.assertEqual([["one", "two"]], calls)
            self.assertEqual(1, provider.calls)
            self.assertEqual(1, len(memory.all("creator_reference_studies")))
