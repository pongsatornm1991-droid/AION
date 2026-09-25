import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.produce_creator_motion import _episode, produce_once, render_kinetic_fallback


class CreatorMotionResilienceTests(unittest.TestCase):
    def test_kinetic_fallback_creates_a_five_second_video_from_the_current_image(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "scene.png"
            target = Path(directory) / "motion.mp4"
            source.write_bytes(b"new-scene")
            with patch("tools.produce_creator_motion.subprocess.run") as run:
                run.side_effect = lambda *args, **kwargs: target.write_bytes(b"new-motion")
                self.assertTrue(render_kinetic_fallback(source, target))
            command = run.call_args.args[0]
            self.assertIn("-t", command)
            self.assertIn("5", command)

    def test_motion_selection_skips_a_quarantined_storyboard(self):
        with patch("tools.produce_creator_motion.CreatorSeriesRegistry") as registry:
            registry.return_value.episodes.return_value = [{
                "id": "ready-short", "status": "assets-ready-for-assembly"
            }]
            self.assertEqual("ready-short", _episode(".")["id"])
            registry.return_value.episodes.assert_called_once_with(skip_invalid=True)

    def test_missing_veo_key_uses_current_image_motion_instead_of_waiting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "assets" / "scene.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"approved-image")
            story = root / "content" / "creator_series" / "ready.json"
            story.parent.mkdir(parents=True)
            story.write_text("{}", encoding="utf-8")
            episode = {
                "id": "ready-short", "status": "assets-ready-for-assembly",
                "format": "illustrated-narrated-short", "file": "content/creator_series/ready.json",
                "scenes": [{"n": 1, "image": "assets/scene.png"}],
            }
            with patch("tools.produce_creator_motion.CreatorSeriesRegistry") as registry, \
                 patch("tools.produce_creator_motion.readiness", return_value={
                     "configured": False, "provider": "gemini-veo", "model": "veo-test", "mode": "automatic-image-to-video"
                 }), \
                 patch("tools.produce_creator_motion.generate_scene_video", return_value={
                     "ok": False, "state": "waiting-for-gemini-video-key"
                 }), \
                 patch("tools.produce_creator_motion.render_kinetic_fallback") as fallback:
                registry.return_value.episodes.return_value = [episode]
                fallback.side_effect = lambda source, target, **_: (Path(target).parent.mkdir(parents=True, exist_ok=True), Path(target).write_bytes(b"motion"), True)[2]
                report = produce_once(root)
            self.assertEqual("motion-assets-complete", report["stage"])
            self.assertFalse(report["provider_configured"])
            self.assertEqual("aion-kinetic-fallback", episode["scenes"][0]["motion_contract"]["provider"])

    def test_persists_the_provider_error_type_when_falling_back(self):
        # Regression for 2026-09-25: a real episode fell back for all 13
        # scenes (every Veo call raised), but motion_contract only ever
        # stored fallback_reason ("provider-failed"), never the exception
        # class name generate_scene_video already returns -- so diagnosing
        # a systematic provider failure after the fact needed re-deriving
        # it from GitHub Actions archaeology instead of just reading the
        # episode file.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "assets" / "scene.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"approved-image")
            story = root / "content" / "creator_series" / "ready.json"
            story.parent.mkdir(parents=True)
            story.write_text("{}", encoding="utf-8")
            episode = {
                "id": "ready-short", "status": "assets-ready-for-assembly",
                "format": "illustrated-narrated-short", "file": "content/creator_series/ready.json",
                "scenes": [{"n": 1, "image": "assets/scene.png"}],
            }
            with patch("tools.produce_creator_motion.CreatorSeriesRegistry") as registry, \
                 patch("tools.produce_creator_motion.readiness", return_value={
                     "configured": True, "provider": "gemini-veo", "model": "veo-test", "mode": "automatic-image-to-video"
                 }), \
                 patch("tools.produce_creator_motion.generate_scene_video", return_value={
                     "ok": False, "state": "provider-failed", "error_type": "PermissionDenied"
                 }), \
                 patch("tools.produce_creator_motion.render_kinetic_fallback") as fallback:
                registry.return_value.episodes.return_value = [episode]
                fallback.side_effect = lambda source, target, **_: (Path(target).parent.mkdir(parents=True, exist_ok=True), Path(target).write_bytes(b"motion"), True)[2]
                produce_once(root)
            self.assertEqual("PermissionDenied", episode["scenes"][0]["motion_contract"]["fallback_error_type"])
