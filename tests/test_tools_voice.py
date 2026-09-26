import os
import unittest
from unittest import mock

from tools.voice import synthesize_thai_voice


class _FakeCommunicate:
    calls = []

    def __init__(self, text, voice):
        self.text = text
        self.voice = voice

    async def save(self, output_path):
        _FakeCommunicate.calls.append((self.text, self.voice, output_path))


class SynthesizeThaiVoiceTests(unittest.TestCase):
    def setUp(self):
        _FakeCommunicate.calls = []

    def test_uses_a_thai_voice_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("THAI_VOICE", None)
            with mock.patch("edge_tts.Communicate", _FakeCommunicate):
                self.assertTrue(synthesize_thai_voice("สวัสดี", "out.mp3"))
        self.assertEqual(1, len(_FakeCommunicate.calls))
        self.assertEqual("th-TH-PremwadeeNeural", _FakeCommunicate.calls[0][1])

    def test_honors_a_thai_voice_override(self):
        with mock.patch.dict(os.environ, {"THAI_VOICE": "th-TH-NiwatNeural"}, clear=False):
            with mock.patch("edge_tts.Communicate", _FakeCommunicate):
                synthesize_thai_voice("สวัสดี", "out.mp3")
        self.assertEqual("th-TH-NiwatNeural", _FakeCommunicate.calls[0][1])

    def test_retries_a_transient_failure_before_succeeding(self):
        attempts = {"n": 0}

        class FlakyCommunicate(_FakeCommunicate):
            async def save(self, output_path):
                attempts["n"] += 1
                if attempts["n"] < 2:
                    raise RuntimeError("transient websocket error")
                await super().save(output_path)

        with mock.patch("edge_tts.Communicate", FlakyCommunicate), mock.patch("time.sleep"):
            self.assertTrue(synthesize_thai_voice("สวัสดี", "out.mp3"))
        self.assertEqual(2, attempts["n"])

    def test_gives_up_and_returns_false_after_repeated_failures(self):
        class AlwaysFailingCommunicate(_FakeCommunicate):
            async def save(self, output_path):
                raise RuntimeError("permanent failure")

        with mock.patch("edge_tts.Communicate", AlwaysFailingCommunicate), mock.patch("time.sleep"):
            self.assertFalse(synthesize_thai_voice("สวัสดี", "out.mp3", attempts=2))


if __name__ == "__main__":
    unittest.main()
