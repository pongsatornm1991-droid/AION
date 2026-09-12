import tempfile
import unittest
from pathlib import Path

from brain.video_quality import VideoQualityGate


class VideoQualityTests(unittest.TestCase):
    def test_missing_video_is_never_eligible(self):
        with tempfile.TemporaryDirectory() as root:
            report = VideoQualityGate(root).assess("missing.mp4")
            self.assertFalse(report["eligible"])
            self.assertIn("missing-or-empty-video", report["reasons"])

    def test_probe_failure_is_never_eligible(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sample.mp4"
            path.write_bytes(b"not-a-video")
            report = VideoQualityGate(root).assess(path)
            self.assertFalse(report["eligible"])
            self.assertTrue(report["reasons"])
