import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.gemini_video import DEFAULT_MODEL, generate_scene_video, readiness


class GeminiVideoTests(unittest.TestCase):
    def test_readiness_never_exposes_the_key(self):
        report = readiness({"GEMINI_API_KEY": "secret-value", "AION_VIDEO_MODEL": "veo-test"})
        self.assertTrue(report["configured"])
        self.assertEqual("gemini-veo", report["provider"])
        self.assertEqual("veo-test", report["model"])
        self.assertNotIn("secret-value", str(report))

    def test_default_model_is_explicit(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(DEFAULT_MODEL, readiness()["model"])


class GenerateSceneVideoTests(unittest.TestCase):
    # Regression, 2026-09-30: every scene of every recent episode was
    # silently falling back to a still-hold clip. Root-caused to two
    # google-genai SDK incompatibilities in this exact call, found by
    # reproducing it against the currently installed SDK version:
    # (1) passing generate_audio=False raises ValueError outright in
    # Gemini Developer API mode (only Enterprise Agent Platform mode
    # accepts it, even as an explicit False), and (2) files.download()'s
    # destination= keyword was removed (it now returns bytes). Both are
    # exercised here against the real installed google.genai.types
    # classes -- only the network-calling Client is mocked -- so a
    # regression on either point fails this test without needing a real
    # API key or network access.
    def test_generate_videos_call_has_no_generate_audio_and_uses_source(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source_image = root / "scene.png"
            source_image.write_bytes(b"fake-png-bytes")
            target = root / "motion" / "01.mp4"

            fake_video = mock.Mock(name="video")
            fake_operation = mock.Mock(done=True)
            fake_operation.response.generated_videos = [mock.Mock(video=fake_video)]

            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
                 mock.patch("google.genai.Client") as mock_client_cls:
                mock_client = mock_client_cls.return_value
                mock_client.models.generate_videos.return_value = fake_operation
                mock_client.files.download.return_value = b"fake-video-bytes"

                report = generate_scene_video("a test prompt", source_image, target)

            self.assertTrue(report["ok"], report)

            call_kwargs = mock_client.models.generate_videos.call_args.kwargs
            self.assertNotIn("prompt", call_kwargs)
            self.assertNotIn("image", call_kwargs)
            self.assertIsNone(call_kwargs["config"].generate_audio)

            download_kwargs = mock_client.files.download.call_args.kwargs
            self.assertNotIn("destination", download_kwargs)
            self.assertEqual(fake_video, download_kwargs["file"])
            self.assertEqual(b"fake-video-bytes", target.read_bytes())
