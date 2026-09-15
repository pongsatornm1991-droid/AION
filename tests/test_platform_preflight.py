import unittest

from brain.platform_preflight import PlatformPreflight


class PlatformPreflightTests(unittest.TestCase):
    def test_never_returns_a_secret_value(self):
        report = PlatformPreflight({"YOUTUBE_CLIENT_ID": "client", "YOUTUBE_CLIENT_SECRET": "secret", "YOUTUBE_REFRESH_TOKEN": "refresh"}).check("youtube")
        self.assertTrue(report["configured"])
        self.assertNotIn("secret", str(report).lower())

    def test_reports_missing_configuration_without_throwing(self):
        report = PlatformPreflight({}).check("instagram")
        self.assertEqual("waiting-for-owner-configuration", report["state"])
        self.assertEqual(2, len(report["missing"]))
