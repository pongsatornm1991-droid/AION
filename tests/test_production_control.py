import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from brain.production_control import ProductionControl, VisualArtifactGate
from tools.production_control import _notify_integrity_alerts


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
            self.assertIn("integrity", report)
            self.assertEqual("healthy", report["integrity"]["state"])
            self.assertEqual("recovering", report["recovery"]["state"])
            self.assertEqual("Production Recovery Manager", report["recovery"]["owner"])
            self.assertIn("evidence_reserve", report)
            self.assertIn("qualified_evidence", report["evidence_reserve"]["counts"])

    def test_a_critical_integrity_finding_escalates_the_overall_state(self):
        # Regression for 2026-09-25: an authorized-but-never-published
        # episode (or any other SystemIntegrity critical finding) must be
        # visible at the top level of this report, not only nested where a
        # reader has to already know to look for it.
        import json as _json
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "content" / "creator_series").mkdir(parents=True); (root / "assets").mkdir()
            Image.new("RGB", (720, 1280), "navy").save(root / "assets" / "01.png")
            Image.new("RGB", (720, 1280), "purple").save(root / "assets" / "02.png")
            episodes_dir = root / "content" / "creator_series"
            for index in range(7):
                episode = _episode()
                episode["id"] = f"test-short-{index}"
                (episodes_dir / f"test-{index}.json").write_text(_json.dumps(episode), encoding="utf-8")
            from brain.memory import MemoryEngine
            memory_root = root / "memory"
            memory = MemoryEngine(memory_root)
            memory.remember("youtube_creator_queue", _json.dumps({
                "episode_id": "stuck-episode", "upload_status": "authorized-for-aion-publish",
            }), memory_type="action")
            import re
            path = memory_root / "youtube_creator_queue.md"
            text = path.read_text(encoding="utf-8")
            old = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime("%Y-%m-%d %H:%M:%S")
            text = re.sub(r"## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", f"## {old}", text)
            path.write_text(text, encoding="utf-8")

            env = dict(self._env())
            env["AION_MEMORY_ROOT"] = str(memory_root)
            report = ProductionControl(root, env).snapshot()

            self.assertEqual("critical", report["integrity"]["state"])
            self.assertEqual("critical", report["state"])
            self.assertEqual("critical", report["component_states"]["integrity"])

    def test_old_style_is_visible_as_a_release_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "content" / "creator_series").mkdir(parents=True); (root / "assets").mkdir()
            Image.new("RGB", (720, 1280), "navy").save(root / "assets" / "01.png")
            Image.new("RGB", (720, 1280), "purple").save(root / "assets" / "02.png")
            (root / "content" / "creator_series" / "test.json").write_text(json.dumps(_episode("legacy")), encoding="utf-8")
            report = ProductionControl(root, self._env()).snapshot()
            self.assertIn("visual-style-not-channel-signature", report["episodes"][0]["release_blockers"])


class NotifyIntegrityAlertsTests(unittest.TestCase):
    def test_sends_one_message_summarizing_every_alert_when_telegram_is_configured(self):
        integrity = {"alerts": [
            {"severity": "critical", "check": "stale-authorization", "detail": "1 episode stuck"},
            {"severity": "warning", "check": "recovery-catalogue-low", "detail": "0 of 57 remain"},
        ]}
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False), \
             patch("tools.telegram.send_telegram_message") as send:
            _notify_integrity_alerts(integrity)
        self.assertEqual(1, send.call_count)
        message = send.call_args.args[0]
        self.assertIn("stale-authorization", message)
        self.assertIn("recovery-catalogue-low", message)

    def test_sends_nothing_when_there_are_no_alerts(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False), \
             patch("tools.telegram.send_telegram_message") as send:
            _notify_integrity_alerts({"alerts": []})
        send.assert_not_called()

    def test_sends_nothing_when_telegram_is_not_configured(self):
        integrity = {"alerts": [{"severity": "critical", "check": "stale-authorization", "detail": "x"}]}
        with patch.dict("os.environ", {}, clear=True), \
             patch("tools.telegram.send_telegram_message") as send:
            _notify_integrity_alerts(integrity)
        send.assert_not_called()

    def test_a_notifier_exception_never_propagates(self):
        integrity = {"alerts": [{"severity": "critical", "check": "stale-authorization", "detail": "x"}]}
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False), \
             patch("tools.telegram.send_telegram_message", side_effect=RuntimeError("boom")):
            _notify_integrity_alerts(integrity)  # must not raise

