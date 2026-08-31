import os
import tempfile
import unittest

from PIL import Image

from tools.reel_render import REEL_SIZE, render_reel_cover


class ReelRenderTests(unittest.TestCase):
    def test_renders_a_vertical_cover(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "cover.png")
            render_reel_cover("What changes when memory returns?", "AION is tracing the answer.", path)
            self.assertTrue(os.path.isfile(path))
            with Image.open(path) as image:
                self.assertEqual(image.size, REEL_SIZE)
