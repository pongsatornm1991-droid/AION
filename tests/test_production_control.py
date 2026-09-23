import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from brain.production_control import ProductionControl, VisualArtifactGate


def _episode(style="aion-neon-diorama-3d-v1", status="production-ready-assets-and-script"):
    return {"id": "test-short", "title": "Why lightning strikes", "topic_key": "lightning rod", "format": "illustrated-narrated-short", "status": status,
            "visual_style": {"id": style}, "scenes": [{"image": "assets/01.png"}, {"image": "assets/02.png"}]}


class ProductionControlTests(unittest.TestCase):
    def _env(self):
        return {"OPENAI_API_KEY": "configured", "GEMINI_API_KEY": "configured", "YOUTUBE_CLIENT_ID": "configured", "YOUTUBE_CLIENT_SECRET": "configured", "YOUTUBE_REFRESH_TOKEN": "configured", "FACEBOOK_PAGE_ACCESS_TOKEN": "configured", "FACEBOOK_PAGE_ID": "configured", "INSTAGRAM_ACCESS_TOKEN": "configured", "INSTAGRAM_BUSINESS_ACCOUNT_ID": "configured"}

    def test_visual_gate_reads_real_vertical_images_and_rejects_exact_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "assets").mkdir()
            image = Image.new("RGB", (720, 1280), "navy")
            image.save(root / "assets" / "01.png"); image.save(root / "assets" / "02.png")
            report = VisualArtifactGate(root).assess(_episode())
            self.assertFalse(report["eligible"])
            self.assertIn("duplicate-scene-image", report["reasons"])

    def test_control_reports_signature_and_provider_health_without_claiming_quota(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "content" / "creator_series").mkdir(parents=True); (root / "assets").mkdir()
            Image.new("RGB", (720, 1280), "navy").save(root / "assets" / "01.png")
            Image.new("RGB", (720, 1280), "purple").save(root / "assets" / "02.png")
            (root / "content" / "creator_series" / "test.json").write_text(json.dumps(_episode()), encoding="utf-8")
            report = ProductionControl(root, self._env()).snapshot()
            self.assertEqual("ready", report["provider_health"]["state"])
            self.assertEqual("unknown-not-inspectable-without-provider-api", report["provider_health"]["quota"])
            self.assertTrue(report["episodes"][0]["release_ready"])
            self.assertEqual(6, report["shorts_buffer"]["missing"])

    def test_old_style_is_visible_as_a_release_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "content" / "creator_series").mkdir(parents=True); (root / "assets").mkdir()
            Image.new("RGB", (720, 1280), "navy").save(root / "assets" / "01.png")
            Image.new("RGB", (720, 1280), "purple").save(root / "assets" / "02.png")
            (root / "content" / "creator_series" / "test.json").write_text(json.dumps(_episode("legacy")), encoding="utf-8")
            report = ProductionControl(root, self._env()).snapshot()
            self.assertIn("visual-style-not-channel-signature", report["episodes"][0]["release_blockers"])

