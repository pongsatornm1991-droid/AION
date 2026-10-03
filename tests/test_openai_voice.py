import os
import tempfile
import unittest
from unittest.mock import patch

from tools.voice import synthesize_reel_voice


class _Response:
    ok = True
    content = b"ID3test-audio"


class OpenAIVoiceTests(unittest.TestCase):
    def test_openai_provider_writes_audio(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai", "OPENAI_API_KEY": "test"}, clear=False), \
             patch("requests.post", return_value=_Response()) as post:
            target = f"{directory}/voice.mp3"
            self.assertTrue(synthesize_reel_voice("A clear sentence.", target))
            with open(target, "rb") as audio:
                self.assertEqual(b"ID3test-audio", audio.read())
            self.assertEqual("https://api.openai.com/v1/audio/speech", post.call_args.args[0])

    def test_openai_provider_passes_a_bounded_requested_speed(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai", "OPENAI_API_KEY": "test"}, clear=False), \
             patch("requests.post", return_value=_Response()) as post:
            self.assertTrue(synthesize_reel_voice("A clear sentence.", f"{directory}/voice.mp3", speed=1.1))
            self.assertEqual(1.1, post.call_args.kwargs["json"]["speed"])

    def test_openai_provider_never_writes_audio_on_failure(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai"}, clear=True):
            self.assertFalse(synthesize_reel_voice("A clear sentence.", f"{directory}/voice.mp3"))

    def test_a_provider_rejection_is_announced_once_with_its_status_and_no_secret(self):
        # 2026-10-03: every speech failure returned a bare False, so a
        # provider-wide problem (quota, key) looked like one bad line and
        # could only be diagnosed from the run log.
        import io
        from contextlib import redirect_stderr
        import tools.voice as voice

        class Rejected:
            ok = False
            status_code = 429
            content = b""

            @staticmethod
            def json():
                return {"error": {"code": "insufficient_quota", "message": "secret-body"}}

        voice._ANNOUNCED.clear()
        captured = io.StringIO()
        with tempfile.TemporaryDirectory() as directory,              patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai", "OPENAI_API_KEY": "sk-secret"}, clear=False),              patch("requests.post", return_value=Rejected()), redirect_stderr(captured):
            self.assertFalse(synthesize_reel_voice("One.", f"{directory}/a.mp3"))
            self.assertFalse(synthesize_reel_voice("Two.", f"{directory}/b.mp3"))
        output = captured.getvalue()
        self.assertEqual(1, output.count("::warning title=openai-speech::HTTP 429 insufficient_quota"))
        self.assertNotIn("sk-secret", output)
        self.assertNotIn("secret-body", output)

