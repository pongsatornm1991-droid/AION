import os
import unittest
from unittest import mock

from tools.gemini_video import DEFAULT_MODEL, readiness


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
