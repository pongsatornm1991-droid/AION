import unittest

from brain.content_router import ContentRouter


class ContentRouterTests(unittest.TestCase):
    def test_keeps_one_story_but_adapts_the_platform_context(self):
        routes = ContentRouter().route(
            "AION follows one question through a changing landscape.",
            "Viewers receive a question and an honest uncertainty.",
        )
        self.assertEqual("AION follows one question through a changing landscape.", routes["instagram"])
        self.assertIn("wider conversation", routes["facebook"])
        self.assertIn("What viewers can take", routes["youtube"])
        self.assertEqual(16, len(routes["content_id"]))
