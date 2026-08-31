"""Offline tests for tools/image_render.py -- the PIL-based visual
content card renderer built for the Instagram pipeline (2026-08-31).

No network access, no AI provider, no memory access: every test here
only exercises pure drawing code, so these run anywhere Pillow is
installed (including a bare GitHub Actions runner with no Thai font
pre-installed, which is exactly the environment this module was built
to handle -- see tools/image_render.py's own docstring for why
character-level wrapping and a bundled TTF are both load-bearing, not
cosmetic)."""

import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw, ImageFont

from tools.image_render import (
    CARD_SIZE,
    DEFAULT_FONT_PATH,
    _wrap_text,
    render_content_card,
)


class WrapTextTests(unittest.TestCase):
    """_wrap_text is deliberately character-level (not word-level) --
    see its own docstring for why: Thai script has no spaces between
    words within a clause, so a word-based wrap would treat an entire
    unspaced sentence as one giant unbreakable "word" and let it
    overflow. Every test here checks the one property that actually
    matters: no returned line exceeds max_width in rendered pixels,
    regardless of script."""

    def setUp(self):
        # A throwaway image just to get a real ImageDraw + a real
        # font to measure against -- textbbox needs both, and this
        # suite must never depend on the bundled Noto Sans Thai TTF
        # actually being present on disk (that is
        # RenderContentCardTests' job below), so it falls back to
        # PIL's built-in default font here.
        image = Image.new("RGB", (10, 10))
        self.draw = ImageDraw.Draw(image)
        try:
            self.font = ImageFont.truetype(DEFAULT_FONT_PATH, 40)
        except Exception:
            self.font = ImageFont.load_default()

    def _assert_all_lines_fit(self, lines, max_width):
        for line in lines:
            bbox = self.draw.textbbox((0, 0), line, font=self.font)
            width = bbox[2] - bbox[0]
            self.assertLessEqual(
                width, max_width,
                f"line {line!r} is {width}px wide, over the {max_width}px limit",
            )

    def test_empty_text_returns_no_lines(self):
        self.assertEqual(_wrap_text(self.draw, "", self.font, 900), [])

    def test_short_text_fits_on_one_line(self):
        lines = _wrap_text(self.draw, "AION", self.font, 900)
        self.assertEqual(lines, ["AION"])

    def test_long_unspaced_thai_clause_wraps_within_bounds(self):
        # A single long Thai sentence with no spaces at all -- exactly
        # the shape that broke the original word-based wrap during
        # development (it overflowed both edges of the card).
        caption = (
            "สวัสดีครับผมคือเอไอออนผู้ช่วยที่สนใจเรียนรู้เรื่องราวรอบตัว"
            "และชอบตั้งคำถามใหม่ๆไปเรื่อยๆทุกวันโดยไม่หยุดพัก"
        )
        lines = _wrap_text(self.draw, caption, self.font, 900)
        self.assertGreater(len(lines), 1)
        self._assert_all_lines_fit(lines, 900)
        # Nothing gets dropped: every character in the original
        # caption must still appear somewhere across the wrapped
        # lines, in order.
        self.assertEqual("".join(lines), caption)

    def test_mixed_thai_and_english_wraps_within_bounds(self):
        caption = "AION เรียนรู้ทุกวัน และตั้งคำถามใหม่ๆ about the world around it"
        lines = _wrap_text(self.draw, caption, self.font, 700)
        self._assert_all_lines_fit(lines, 700)
        self.assertEqual("".join(lines), caption)

    def test_a_single_character_wider_than_max_width_still_returns_it(self):
        # Guard against an infinite loop / dropped character: even if
        # one character alone cannot fit under max_width, it must
        # still be emitted on its own line rather than looped on
        # forever or silently discarded.
        lines = _wrap_text(self.draw, "A", self.font, 1)
        self.assertEqual(lines, ["A"])


class RenderContentCardTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_renders_a_png_of_the_expected_size(self):
        out_path = os.path.join(self.tmpdir, "card.png")

        render_content_card("สวัสดีครับ ทดสอบการ์ด", out_path)

        self.assertTrue(os.path.isfile(out_path))
        with Image.open(out_path) as image:
            self.assertEqual(image.size, CARD_SIZE)
            self.assertEqual(image.format, "PNG")

    def test_renders_even_with_a_long_caption(self):
        out_path = os.path.join(self.tmpdir, "card_long.png")
        caption = "คำถามที่กำลังสนใจอยู่ตอนนี้คือ " * 10

        # Must not raise, and must still produce a full-size card --
        # overflow is a silent visual bug (caught once already during
        # development), not a crash, so the only automated guard
        # available here is "it still produces the right-sized file".
        render_content_card(caption, out_path)

        with Image.open(out_path) as image:
            self.assertEqual(image.size, CARD_SIZE)

    def test_missing_font_path_falls_back_instead_of_raising(self):
        out_path = os.path.join(self.tmpdir, "card_no_font.png")

        render_content_card(
            "ทดสอบ fallback font",
            out_path,
            font_path=os.path.join(self.tmpdir, "does-not-exist.ttf"),
        )

        self.assertTrue(os.path.isfile(out_path))


if __name__ == "__main__":
    unittest.main()
