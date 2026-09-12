import unittest

from main import _format_reflection_telegram_report


class ReflectionNotificationTests(unittest.TestCase):
    def test_belief_notification_never_exposes_numeric_confidence(self):
        message = _format_reflection_telegram_report({
            "stage": "raised", "originated_type": "belief", "statement": "A careful belief",
            "confidence": 0.70,
        })
        self.assertNotIn("0.70", message)
        self.assertNotIn("ความมั่นใจ", message)
        self.assertIn("สถานะหลักฐาน", message)
