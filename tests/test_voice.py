import os
import tempfile
import unittest
from unittest.mock import patch

from tools.voice import synthesize_reel_voice


class _Response:
    ok = True
    content = b"ID3test-audio"


class VoiceTests(unittest.TestCase):
    def test_openai_provider_writes_audio(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai", "OPENAI_API_KEY": "test"}, clear=False), \
             patch("requests.post", return_value=_Response()) as post:
            target = f"{directory}/voice.mp3"
            self.assertTrue(synthesize_reel_voice("A clear sentence.", target))
            with open(target, "rb") as audio:
                self.assertEqual(b"ID3test-audio", audio.read())
            self.assertEqual("https://api.openai.com/v1/audio/speech", post.call_args.args[0])

    def test_openai_provider_never_writes_audio_on_failure(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"REEL_VOICE_PROVIDER": "openai"}, clear=True):
            self.assertFalse(synthesize_reel_voice("A clear sentence.", f"{directory}/voice.mp3"))
