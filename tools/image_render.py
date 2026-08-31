"""Pure-code visual content card renderer -- draws AION's branded
Instagram/Facebook image cards with PIL. No AI provider call, no
network access, no memory access: given a caption string and an
output path, it draws the same picture every time. Kept as its own
top-level "tools" module (like tools/facebook.py, tools/instagram.py)
because it is a mechanical drawing operation, not a content decision --
brain/visual_content.py decides WHAT caption to draw and WHERE the
image should end up; this module only knows HOW to draw one.

Visual identity: matches AION's existing profile-picture design
language (see the "Instagram expansion" audit section) -- a dark,
near-black background with a cyan-teal accent glow, a small "AION"
watermark in the corner so the card is recognizable even without the
avatar attached, and the caption itself set in Noto Sans Thai (bundled
in this repo at assets/fonts/NotoSansThai-Regular.ttf, since Thai text
otherwise renders as empty boxes on a bare Ubuntu GitHub Actions
runner, which has no Thai-capable font installed by default).

Deliberately simple: solid background + soft radial-ish glow band +
centered word-wrapped caption + corner watermark. No external image
assets, no template library -- easy to keep free-tier (nothing here
costs money to run, unlike Gemini's paid image-generation models,
which this project has declined to use since Phase 10).
"""

import os

from PIL import Image, ImageDraw, ImageFont

# Repo-relative so this works the same whether invoked from the repo
# root (local CLI use) or from a GitHub Actions runner's checkout --
# both put this file at tools/image_render.py, so climbing one
# directory from this file's own location always lands on the repo
# root regardless of the process's current working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FONT_PATH = os.path.join(
    _REPO_ROOT, "assets", "fonts", "NotoSansThai-Regular.ttf"
)

CARD_SIZE = (1080, 1080)
BACKGROUND_COLOR = (10, 14, 18)          # near-black, matches the avatar's mood
GLOW_COLOR = (34, 211, 238)              # cyan-teal accent, matches the avatar
TEXT_COLOR = (235, 245, 248)
WATERMARK_COLOR = (34, 211, 238)


def _load_font(size, font_path=None):
    font_path = font_path or DEFAULT_FONT_PATH
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        # Missing/unreadable font file: fall back to PIL's built-in
        # bitmap font rather than crashing the whole render. Thai
        # glyphs will not render correctly with this fallback, but an
        # ugly-but-present image beats a hard failure in a scheduled
        # job -- callers can check the returned font's type if they
        # need to detect this case.
        return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    """Wrap text to max_width, measured in actual rendered pixels.

    Deliberately character-level, not word-level: Thai script (this
    project's primary caption language, per SocialContentGenerator's
    drafting prompt) does not use spaces between words within a
    sentence, only between clauses/sentences -- a naive str.split()
    word-wrap treats an entire unspaced Thai clause as one giant
    "word" and lets it overflow the card's edges uncorrected (caught
    by eye during development: a first render cut off both edges of
    the first line). Wrapping character-by-character instead
    guarantees every line fits max_width regardless of script, at the
    minor cost of occasionally breaking mid-word in an English
    caption -- an acceptable trade for a short, mostly-Thai content
    card."""

    if not text:
        return []

    lines = []
    current = ""

    for char in text:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        fits = bbox[2] - bbox[0] <= max_width

        if fits or not current:
            current = candidate
        else:
            lines.append(current)
            current = char

    if current:
        lines.append(current)

    return lines


def render_content_card(
    caption,
    out_path,
    font_path=None,
    size=CARD_SIZE,
    watermark="AION",
):
    """Draw one branded square content card and save it as a PNG.

    caption: the short Thai text to display, centered.
    out_path: where to write the PNG (parent directories are created
      if missing).
    Returns out_path on success. Raises ValueError for an empty
    caption -- there is nothing sensible to draw without one.
    """

    caption = str(caption or "").strip()
    if not caption:
        raise ValueError("caption cannot be empty.")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    width, height = size
    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    # A soft horizontal glow band across the middle third, evoking the
    # cyan hair/iris glow in AION's profile picture without trying to
    # reproduce a photorealistic portrait in code.
    band_top = int(height * 0.38)
    band_bottom = int(height * 0.62)
    band_height = band_bottom - band_top
    for offset in range(band_height):
        # Fade opacity toward the edges of the band for a soft glow
        # rather than a hard-edged rectangle.
        distance_from_center = abs(offset - band_height / 2) / (band_height / 2)
        alpha = max(0.0, 1.0 - distance_from_center)
        blended = tuple(
            int(BACKGROUND_COLOR[i] + (GLOW_COLOR[i] - BACKGROUND_COLOR[i]) * alpha * 0.18)
            for i in range(3)
        )
        draw.line([(0, band_top + offset), (width, band_top + offset)], fill=blended)

    caption_font = _load_font(56, font_path=font_path)
    margin = 100
    max_text_width = width - 2 * margin

    lines = _wrap_text(draw, caption, caption_font, max_text_width)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=caption_font)
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = 20
    total_text_height = sum(line_heights) + line_spacing * max(0, len(lines) - 1)
    current_y = (height - total_text_height) / 2

    for line, line_height in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=caption_font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) / 2
        draw.text((x, current_y), line, font=caption_font, fill=TEXT_COLOR)
        current_y += line_height + line_spacing

    watermark_font = _load_font(34, font_path=font_path)
    watermark_text = str(watermark or "")
    if watermark_text:
        bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
        wm_width = bbox[2] - bbox[0]
        wm_x = width - margin - wm_width
        wm_y = height - 80
        draw.text(
            (wm_x, wm_y), watermark_text, font=watermark_font, fill=WATERMARK_COLOR,
        )

    image.save(out_path, format="PNG")
    return out_path
