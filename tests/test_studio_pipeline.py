import json
import tempfile
import unittest
from pathlib import Path

from brain.studio_pipeline import StudioPipeline


class StudioPipelineTests(unittest.TestCase):
    def test_exposes_the_real_owner_for_a_studio_status(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "content" / "creator_series"; folder.mkdir(parents=True)
            (folder / "e.json").write_text(json.dumps({
                "id": "e", "series": "A", "title": "Episode", "status": "assets-ready-for-assembly",
                "format": "illustrated-narrated-short", "scene_seconds": 5, "target_duration_seconds": 15,
                "audience_promise": "A clear benefit for curious viewers of every age.", "wonder_hook": "Why does this happen?",
                "creative_device": "journey", "age_layers": {"children": "Ask", "family": "Talk", "deeper": "Test"},
                "science_boundary": "A boundary.", "sources": [{"url": "https://one"}, {"url": "https://two"}],
                "scenes": [{"n": n, "visual": "AION explores.", "narration": "AION asks."} for n in range(3)],
            }), encoding="utf-8")
            card = StudioPipeline(root).snapshot()["active"][0]
            self.assertEqual("Audio Producer", card["owner"])
            self.assertEqual("Video QA Agent", card["next_owner"])
