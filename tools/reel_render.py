"""Render concise, caption-led AION Reels from the visual library.

Uses Pillow for the branded cover and ffmpeg (available on GitHub's Ubuntu
runners) for a subtle camera motion MP4.  It deliberately has no network or
publishing logic.
"""

import hashlib
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps

from tools.image_render import (
    BACKGROUND_COLOR, CONTENT_LIBRARY_DIR, DEFAULT_FONT_PATH, GLOW_COLOR,
    TEXT_COLOR, _background_paths,
)

REEL_SIZE = (1080, 1920)


def _font(size):
    try:
        return ImageFont.truetype(DEFAULT_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words, lines, current = str(text).split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    return lines + ([current] if current else [])


def render_reel_cover(hook, thought, output_path):
    """Create the readable first frame for a vertical AION Reel."""
    paths = _background_paths()
    image = Image.new("RGB", REEL_SIZE, BACKGROUND_COLOR)
    if paths:
        chosen = paths[int.from_bytes(hashlib.sha256(str(hook).encode()).digest()[:4], "big") % len(paths)]
        with Image.open(chosen) as source:
            image = ImageOps.fit(source.convert("RGB"), REEL_SIZE)
    overlay = Image.new("RGBA", REEL_SIZE, (0, 0, 0, 125))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    margin, hook_font, thought_font = 90, _font(78), _font(44)
    y = 210
    for line in _wrap(draw, hook, hook_font, REEL_SIZE[0] - 2 * margin):
        draw.text((margin, y), line, font=hook_font, fill=TEXT_COLOR)
        y += 100
    y += 55
    for line in _wrap(draw, thought, thought_font, REEL_SIZE[0] - 2 * margin):
        draw.text((margin, y), line, font=thought_font, fill=TEXT_COLOR)
        y += 64
    draw.text((margin, 1760), "AION  •  becoming in public", font=_font(32), fill=GLOW_COLOR)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def render_reel(hook, thought, output_path, duration=12):
    """Create a 9:16 MP4 with slow motion from an AION cover image."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render MP4 Reels; GitHub Actions runners include it.")
    cover = os.path.splitext(output_path)[0] + "-cover.png"
    render_reel_cover(hook, thought, cover)
    subprocess.run([
        ffmpeg, "-y", "-loop", "1", "-i", cover,
        "-vf", "zoompan=z='min(zoom+0.0006,1.08)':d=360:s=1080x1920,format=yuv420p",
        "-t", str(duration), "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path,
    ], check=True, capture_output=True, text=True)
    return output_path
