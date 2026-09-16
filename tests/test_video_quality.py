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

    def test_vertical_sunday_feature_is_not_mistaken_for_widescreen_longform(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "feature.mp4"
            path.write_bytes(b"video")
            gate = VideoQualityGate(root)
            gate._probe = lambda _path: ({
                "format": {"duration": "120"},
                "streams": [
                    {"codec_type": "video", "width": 1080, "height": 1920},
                    {"codec_type": "audio"},
                ],
            }, None)
            signature = {"mean_luma": 30, "variance": 10, "pixels": b"different"}
            gate._sample_frames = lambda _path, _duration: ([
                {**signature, "pixels": bytes([1])},
                {**signature, "pixels": bytes([2])},
                {**signature, "pixels": bytes([3])},
            ], None)
            self.assertTrue(gate.assess(path, "long-form")["eligible"])

    def test_shorter_than_one_minute_never_passes_short_quality_gate(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "short.mp4"
            path.write_bytes(b"video")
            gate = VideoQualityGate(root)
            gate._probe = lambda _path: ({"format": {"duration": "25"}, "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920}, {"codec_type": "audio"},
            ]}, None)
            signature = {"mean_luma": 30, "variance": 10}
            gate._sample_frames = lambda _path, _duration: ([
                {**signature, "pixels": bytes([1])}, {**signature, "pixels": bytes([2])}, {**signature, "pixels": bytes([3])},
            ], None)
            report = gate.assess(path, "short")
            self.assertFalse(report["eligible"])
            self.assertIn("short-must-be-60-to-180-seconds", report["reasons"])
