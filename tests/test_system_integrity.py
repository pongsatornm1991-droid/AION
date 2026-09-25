import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from brain.initiative import AutonomousInitiative
from brain.memory import MemoryEngine
from brain.system_integrity import SystemIntegrity


def _age_last_entry(root, category, when):
    """Rewrite the most recently written entry's timestamp for age tests.

    MemoryEngine.remember() always stamps `datetime.now()`; there is no
    public way to backdate an entry, and this module's whole purpose is
    judging entry *age*, so tests fabricate it directly the same way a
    human auditing the file by hand would recognize an old entry: by its
    timestamp header line.
    """
    path = Path(root) / f"{category}.md"
    text = path.read_text(encoding="utf-8")
    stamped = when.strftime("%Y-%m-%d %H:%M:%S")
    # Only the LAST "## <timestamp>" header (the entry just written) is
    # replaced, so earlier fixture entries in the same test are unaffected.
    matches = list(re.finditer(r"\n## \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\n", text))
    assert matches, "no timestamped entry found to age"
    start, end = matches[-1].span()
    text = text[:start] + f"\n## {stamped}\n" + text[end:]
    path.write_text(text, encoding="utf-8")


class SystemIntegrityTests(unittest.TestCase):
    def test_flags_an_episode_authorized_for_days_without_reaching_youtube(self):
        # Regression for 2026-09-25: this exact condition (authorized,
        # never published) persisted silently for at least 5 days because
        # an expired YouTube OAuth token failed every attempt while the
        # workflow still reported success.
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "stuck-episode", "upload_status": "authorized-for-aion-publish",
            }), memory_type="action")
            _age_last_entry(root, "youtube_creator_queue", datetime.now(timezone.utc) - timedelta(hours=72))

            report = SystemIntegrity(memory, root).snapshot()

            self.assertEqual("critical", report["state"])
            checks = [a["check"] for a in report["alerts"]]
            self.assertIn("stale-authorization", checks)
            self.assertEqual("stuck-episode", report["checks"]["stale_authorizations"][0]["episode_id"])

    def test_does_not_flag_a_recently_authorized_episode(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "fresh-episode", "upload_status": "authorized-for-aion-publish",
            }), memory_type="action")

            report = SystemIntegrity(memory, root).snapshot()

            self.assertEqual([], report["checks"]["stale_authorizations"])

    def test_does_not_flag_an_episode_that_actually_published(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "done-episode", "upload_status": "authorized-for-aion-publish",
            }), memory_type="action")
            _age_last_entry(root, "youtube_creator_queue", datetime.now(timezone.utc) - timedelta(hours=72))
            memory.remember("youtube_creator_queue", json.dumps({
                "episode_id": "done-episode", "upload_status": "published",
                "youtube": {"video_id": "abc123", "privacy_status": "public"},
            }), memory_type="action")

            report = SystemIntegrity(memory, root).snapshot()

            self.assertEqual([], report["checks"]["stale_authorizations"])
            self.assertEqual("healthy", report["state"])

    def _episode_with_motion(self, directory, episode_id, providers):
        series = Path(directory) / "content" / "creator_series"
        series.mkdir(parents=True, exist_ok=True)
        (series / f"{episode_id}.json").write_text(json.dumps({
            "id": episode_id,
            "scenes": [
                {"n": index + 1, "motion_contract": {"provider": provider}}
                for index, provider in enumerate(providers)
            ],
        }), encoding="utf-8")

    def test_flags_every_recent_episode_using_only_the_fallback_renderer(self):
        # Regression for 2026-09-25: found via a jerky-motion report that
        # all 13 scenes of a real episode fell back because Veo failed on
        # every single call -- this is exactly the pattern this check is
        # meant to surface automatically instead of needing a manual report
        # to trigger the investigation.
        with tempfile.TemporaryDirectory() as directory:
            for index in range(3):
                self._episode_with_motion(directory, f"ep-{index}", ["aion-static-fallback"] * 3)
            memory = MemoryEngine(Path(directory) / "memory")

            report = SystemIntegrity(memory, directory).snapshot()

            checks = [a["check"] for a in report["alerts"]]
            self.assertIn("motion-fallback-rate", checks)
            self.assertEqual(1.0, report["checks"]["motion_fallback"]["rate"])

    def test_does_not_flag_when_the_real_provider_is_succeeding(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(3):
                self._episode_with_motion(directory, f"ep-{index}", ["gemini-veo", "gemini-veo", "aion-static-fallback"])
            memory = MemoryEngine(Path(directory) / "memory")

            report = SystemIntegrity(memory, directory).snapshot()

            checks = [a["check"] for a in report["alerts"]]
            self.assertNotIn("motion-fallback-rate", checks)

    def test_flags_a_nearly_exhausted_recovery_catalogue(self):
        catalogue = (
            ("insect-science", "Why do fireflies glow in the dark?", "metaphor"),
            ("water-science", "Why do lakes freeze from the top down?", "metaphor"),
        )
        with tempfile.TemporaryDirectory() as root, patch.object(AutonomousInitiative, "RECOVERY_INQUIRIES", catalogue):
            memory = MemoryEngine(root)
            # Both catalogue questions are asked; raise them for real so
            # their statement is parseable the same way
            # AutonomousInitiative._asked_recovery_statements() reads it.
            from brain.curiosity import CuriosityEngine
            curiosity = CuriosityEngine(memory)
            for _, question, _ in catalogue:
                curiosity.raise_question(question, "Cite two sources.", tags=["shorts-recovery"])

            report = SystemIntegrity(memory, root).snapshot()

            checks = [a["check"] for a in report["alerts"]]
            self.assertIn("recovery-catalogue-low", checks)
            self.assertEqual(0, report["checks"]["recovery_catalogue"]["remaining"])

    def test_healthy_state_when_nothing_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryEngine(Path(directory) / "memory")
            report = SystemIntegrity(memory, directory).snapshot()
            self.assertEqual("healthy", report["state"])
            self.assertEqual([], report["alerts"])
