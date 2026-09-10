import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.image_render import render_visual_only


class VisualOnlyRendererTests(unittest.TestCase):
    def test_creates_a_square_artwork_without_needing_caption_text(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "visual.png"
            result = render_visual_only("AION explores a new question", str(path))
            self.assertEqual(str(path), result)
            self.assertTrue(path.is_file())
            with Image.open(path) as image:
                self.assertEqual((1080, 1080), image.size)
