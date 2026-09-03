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

The generated AION visual reference supplies an atmospheric background,
kept close to its original vibrancy (reader feedback: an earlier
version's full-card dark overlay looked too heavy/dull -- "ทึบ"). A
soft dark scrim now sits only directly behind the caption block, with
a cyan accent bar marking it, and a small corner watermark -- the rest
of the artwork stays untouched. It remains a deterministic, free
fallback: an unavailable future image-generation provider can never
stop the Instagram cycle from publishing.
"""

import hashlib
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    # Real Thai word segmentation -- lets the caption wrap on whole
    # words instead of mid-word. Ships its dictionary inside the
    # package (see tools/image_render.py's module docstring for why
    # this file must stay network-free at *runtime*): the trie is
    # loaded from disk on import, nothing is fetched over the network,
    # so this stays safe to call from an offline GitHub Actions
    # runner exactly like the rest of this module.
    from pythainlp.tokenize import word_tokenize as _thai_word_tokenize
except ImportError:  # pragma: no cover -- exercised only if the
    # optional dependency somehow isn't installed; _tokenize_words()
    # falls back to grapheme-cluster wrapping in that case so a render
    # is still possible rather than crashing a scheduled job.
    _thai_word_tokenize = None

# Repo-relative so this works the same whether invoked from the repo
# root (local CLI use) or from a GitHub Actions runner's checkout --
# both put this file at tools/image_render.py, so climbing one
# directory from this file's own location always lands on the repo
# root regardless of the process's current working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FONT_PATH = os.path.join(
    _REPO_ROOT, "assets", "fonts", "NotoSansThai-Regular.ttf"
)
BACKGROUND_ART_PATH = os.path.join(
    _REPO_ROOT, "assets", "visual-references", "aion-learning-v1.png"
)
CONTENT_LIBRARY_DIR = os.path.join(
    _REPO_ROOT, "assets", "content-library", "aion-core"
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


# Thai leading vowels: written before the consonant they attach to but
# pronounced after it (เ, แ, โ, ใ, ไ). A line break must never land
# between one of these and its consonant -- that literally separates a
# vowel from the letter it belongs to and reads as garbled Thai.
_THAI_LEADING_VOWELS = "เแโใไ"

# Marks that attach to the PRECEDING consonant (vowel signs above/
# below/after, tone marks, and a few rarer diacritics). A line must
# never start with one of these -- an orphaned tone mark or vowel sign
# with no base letter is the exact defect this replaces.
_THAI_TRAILING_MARKS = "ะัาำิีึืุูๅ่้๊๋์ํ๎ๆ"


def _thai_clusters(text):
    """Split text into grapheme-safe units: each unit is one visual
    Thai syllable-cluster (a leading vowel plus its consonant, or a
    consonant plus its trailing vowel/tone marks) or one plain
    character. Wrapping by these units instead of raw characters keeps
    every mark attached to its base letter across a line break."""

    units = []
    i = 0
    n = len(text)

    while i < n:
        cluster = text[i]
        i += 1

        if cluster in _THAI_LEADING_VOWELS:
            # Absorb the consonant (or whatever follows) this vowel
            # attaches to, so the pair can never be split apart.
            while i < n and text[i] in _THAI_LEADING_VOWELS:
                cluster += text[i]
                i += 1
            if i < n:
                cluster += text[i]
                i += 1

        while i < n and text[i] in _THAI_TRAILING_MARKS:
            cluster += text[i]
            i += 1

        units.append(cluster)

    return units


def _tokenize_words(text):
    """Split text into whole words. Thai script (this project's
    primary caption language, per SocialContentGenerator's drafting
    prompt) has no spaces between words within a sentence, so a naive
    str.split() would treat an entire clause as one giant unbreakable
    "word" -- pythainlp's tokenizer solves that properly (see the
    import above). Falls back to _thai_clusters() -- syllable-safe but
    not word-safe -- only if that optional dependency is missing, so a
    render is still possible either way."""

    if _thai_word_tokenize is not None:
        try:
            return _thai_word_tokenize(text, engine="newmm")
        except Exception:
            pass
    return _thai_clusters(text)


def _wrap_text(draw, text, font, max_width):
    """Wrap text to max_width, measured in actual rendered pixels.

    Wraps on whole words (via _tokenize_words()), never mid-word: an
    earlier character-level version could land a break between a
    leading vowel and its consonant, or split a real word in half
    (caught from a live sample: "ข้อมูล" -- "information" -- broken
    into "ข้" / "อมูล" across two lines, reading as garbled,
    disconnected Thai even though every mark stayed attached to its
    base letter). Word-level wrapping is what a person doing this by
    hand would do, so it is now the default; the one remaining edge
    case is a single token wider than max_width all by itself (a long
    compound noun, or an unbroken run of Latin characters) -- that
    token alone is split by _thai_clusters() as a last resort, so it
    still cannot overflow the card's edges."""

    if not text:
        return []

    def fits(candidate):
        bbox = draw.textbbox((0, 0), candidate, font=font)
        return bbox[2] - bbox[0] <= max_width

    words = _tokenize_words(text)
    lines = []
    current = ""

    def flush():
        nonlocal current
        if current:
            lines.append(current)
            current = ""

    for word in words:
        candidate = current + word
        if fits(candidate):
            current = candidate
            continue

        if current and fits(word):
            # The word alone fits fine -- it only overflowed combined
            # with what came before, so it starts the next line whole.
            flush()
            current = word
            continue

        # The word overflows max_width even on its own empty line:
        # fall back to syllable-safe splitting for just this one
        # token so it still cannot run off the card.
        flush()
        for cluster in _thai_clusters(word):
            piece = current + cluster
            if fits(piece) or not current:
                current = piece
            else:
                flush()
                current = cluster

    flush()
    return lines


def _background_paths():
    """Return the bundled library in a stable order, with the legacy art first."""
    paths = [BACKGROUND_ART_PATH]
    try:
        paths.extend(
            os.path.join(CONTENT_LIBRARY_DIR, filename)
            for filename in sorted(os.listdir(CONTENT_LIBRARY_DIR))
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        )
    except OSError:
        pass
    return [path for path in paths if os.path.isfile(path)]


def _create_background(size, seed=""):
    """Build a readable branded background, selecting a stable library visual."""
    width, height = size
    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)

    paths = _background_paths()
    if paths:
        # A caption always maps to the same artwork.  This avoids a random
        # retry changing a post's visual identity while still rotating the
        # pre-generated library naturally across different thoughts.
        digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
        selected = paths[int.from_bytes(digest[:4], "big") % len(paths)]
        try:
            with Image.open(selected) as source:
                image = ImageOps.fit(source.convert("RGB"), (width, height))
        except OSError:
            pass

    # A light global tint only, for mood and to keep every library photo
    # reading as one visual family -- readable contrast for the caption
    # itself comes from a separate, localized scrim (see _text_scrim())
    # placed just behind the text block, not from darkening the whole
    # card. A heavier full-card overlay looked too flat and dull.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 55))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _text_scrim(size, top_y, bottom_y, max_alpha=165, fade=110):
    """A soft dark gradient panel behind the caption block ONLY --
    not the whole card. Reader feedback on an earlier version (a
    full-card dark overlay plus a glow band across the middle) was
    that it looked too heavy/dull ("ทึบ") and hid the artwork's best
    part. This keeps every pixel outside the text block at the
    background's original vibrancy, and only dims the strip the
    caption actually sits on, fading in/out over `fade` pixels so the
    edge is soft rather than a hard-edged box."""

    width, height = size
    scrim = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)

    fade_in_start = max(0, top_y - fade)
    fade_out_end = min(height, bottom_y + fade)

    for y in range(fade_in_start, fade_out_end):
        if y < top_y:
            alpha = int(max_alpha * (y - fade_in_start) / max(1, top_y - fade_in_start))
        elif y > bottom_y:
            alpha = int(max_alpha * (1 - (y - bottom_y) / max(1, fade_out_end - bottom_y)))
        else:
            alpha = max_alpha
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    return scrim


def render_content_card(
    caption,
    out_path,
    font_path=None,
    size=CARD_SIZE,
    watermark="AION",
):
    """Draw one branded square content card and save it as a PNG.

    caption: the short Thai text to display.
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
    image = _create_background((width, height), seed=caption).convert("RGBA")
    draw = ImageDraw.Draw(image)

    caption_font = _load_font(56, font_path=font_path)
    margin = 100
    accent_gap = 36
    max_text_width = width - 2 * margin - accent_gap

    lines = _wrap_text(draw, caption, caption_font, max_text_width)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=caption_font)
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = 22
    total_text_height = sum(line_heights) + line_spacing * max(0, len(lines) - 1)
    # Lower two-thirds of the card, not dead-center -- leaves the
    # background art's upper portion (usually its most interesting
    # part) completely unobstructed.
    start_y = height * 0.58 - total_text_height / 2

    scrim_top = max(0, int(start_y - 50))
    scrim_bottom = min(height, int(start_y + total_text_height + 70))
    image = Image.alpha_composite(
        image, _text_scrim((width, height), scrim_top, scrim_bottom)
    )
    draw = ImageDraw.Draw(image)

    # A slim accent bar marks the caption block instead of a kicker
    # label or logo badge -- reader feedback was to drop those and
    # keep the card simple.
    bar_x = margin
    draw.rounded_rectangle(
        [bar_x, start_y - 6, bar_x + 8, start_y + total_text_height + 6],
        radius=4, fill=GLOW_COLOR,
    )

    current_y = start_y
    for line, line_height in zip(lines, line_heights):
        draw.text(
            (margin + accent_gap, current_y), line, font=caption_font, fill=TEXT_COLOR,
        )
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

    image.convert("RGB").save(out_path, format="PNG")
    return out_path
