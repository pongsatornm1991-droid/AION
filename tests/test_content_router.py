import unittest

from brain.content_router import ContentRouter
from brain.identity_disclosure import DISCLOSURE_TH


class ContentRouterTests(unittest.TestCase):
    def test_keeps_one_story_but_adapts_the_platform_context(self):
        routes = ContentRouter().route(
            "AION follows one question through a changing landscape.",
            "Viewers receive a question and an honest uncertainty.",
        )
        self.assertTrue(routes["instagram"].startswith("AION follows one question through a changing landscape."))
        self.assertIn("wider conversation", routes["facebook"])
        self.assertIn(DISCLOSURE_TH, routes["facebook"])
        self.assertIn(DISCLOSURE_TH, routes["instagram"])
        self.assertIn("What viewers can take", routes["youtube"])
        self.assertNotIn(DISCLOSURE_TH, routes["youtube"])
        self.assertEqual(16, len(routes["content_id"]))
