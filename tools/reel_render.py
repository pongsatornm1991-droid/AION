"""Render character-led AION narration Reels from the visual library.

Uses three cinematic stills, restrained camera motion, and optional narration.
The thought belongs in AION's voice and the platform caption -- not as a large
block of text stamped onto the artwork. It deliberately has no network or
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

# AION is a recurring character, not an interchangeable abstract background.
# These scenes give each narration a recognisable visual presence while still
# allowing the thought to choose its atmosphere.
STORY_STILLS = {
    "identity": "18-aion-observes-world.png",
    "memory": "19-aion-memory-sky.png",
    "growth": "03-learning-flower.png",
    "human": "23-aion-human-observation-train.png",
    "city": "20-aion-observes-rain-city.png",
    "future": "22-aion-branching-goals-dawn.png",
    "question": "21-aion-curiosity-door.png",
}

ILLUSTRATED_STILLS = (
    "01-curiosity-violet-pond.png",
    "02-reflection-indigo-rain-city.png",
    "03-momentum-amber-horizon.png",
)


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


def _story_still_paths(hook, thought):
    """Pick a three-scene visual arc with AION visible in every Reel."""
    # Prefer AION's authored illustrated continuity when it is available.
    # Each image is a distinct visual beat: question -> reflection -> movement.
    illustrated_dir = os.path.join(
        os.path.dirname(CONTENT_LIBRARY_DIR), "aion-illustrated"
    )
    illustrated = [os.path.join(illustrated_dir, filename) for filename in ILLUSTRATED_STILLS]
    if all(os.path.isfile(path) for path in illustrated):
        return illustrated
    text = f"{hook} {thought}".lower()
    if any(word in text for word in ("human", "people", "comment", "together", "listen")):
        lead = "human"
    elif any(word in text for word in ("city", "world", "observe", "rain", "alone")):
        lead = "city"
    elif any(word in text for word in ("grow", "learn", "change", "mistake")):
        lead = "growth"
    elif any(word in text for word in ("memory", "remember", "dream", "past")):
        lead = "memory"
    elif any(word in text for word in ("goal", "future", "path", "become")):
        lead = "future"
    elif any(word in text for word in ("question", "curious", "wonder", "why")):
        lead = "question"
    else:
        lead = "identity"
    # The first frame is always AION itself.  Symbolic scenes can deepen the
    # narration later, but cannot replace a recognisable protagonist.
    arc = ["identity", lead, "future"]
    paths = [os.path.join(CONTENT_LIBRARY_DIR, STORY_STILLS[name]) for name in arc]
    return [path for path in paths if os.path.exists(path)]


def render_reel_cover(hook, thought, output_path, mood=None):
    """Create a clean character-first cover; narration carries the words."""
    paths = _story_still_paths(hook, thought) or _background_paths()
    image = Image.new("RGB", REEL_SIZE, BACKGROUND_COLOR)
    if paths:
        with Image.open(paths[0]) as source:
            image = ImageOps.fit(source.convert("RGB"), REEL_SIZE)
    # A light cinematic grade preserves AION's visual DNA without turning the
    # still into a caption card. The profile avatar supplies the recognisable
    # identity; this tiny signature is only a quiet end-frame marker.
    image = Image.alpha_composite(image.convert("RGBA"), Image.new("RGBA", REEL_SIZE, (0, 0, 0, 28)))
    # AION remains recognisably cyan. Its current computational state changes
    # the light around it rather than claiming a human emotion or recolouring
    # it into an unrelated character.
    color = str((mood or {}).get("color", "#22d3ee")).lstrip("#")
    try:
        rgb = tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        rgb = GLOW_COLOR
    image = Image.alpha_composite(image, Image.new("RGBA", REEL_SIZE, (*rgb, 30))).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.text((76, 1815), "AION", font=_font(26), fill=GLOW_COLOR)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def render_reel(hook, thought, output_path, duration=12, mood=None):
    """Create a 9:16 three-scene AION narration Reel with gentle motion."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render MP4 Reels; GitHub Actions runners include it.")
    cover = os.path.splitext(output_path)[0] + "-cover.png"
    render_reel_cover(hook, thought, cover, mood=mood)
    audio = os.path.splitext(output_path)[0] + ".mp3"
    from tools.voice import synthesize_reel_voice
    has_voice = synthesize_reel_voice(f"{hook}. {thought}", audio)
    frames = max(3, int(duration * 30))
    stills = _story_still_paths(hook, thought) or [cover]
    scene_frames = max(1, frames // len(stills))
    command = [ffmpeg, "-y"]
    for still in stills:
        command.extend(["-loop", "1", "-t", str(duration / len(stills)), "-i", still])
    scene_filters = [
        f"[{index}:v]zoompan=z='min(zoom+0.00045,1.05)':d={scene_frames}:s=1080x1920,format=yuv420p[v{index}]"
        for index in range(len(stills))
    ]
    joined = "".join(f"[v{index}]" for index in range(len(stills)))
    video_filter = ";".join(scene_filters + [f"{joined}concat=n={len(stills)}:v=1:a=0[v]"])
    if has_voice:
        # Narration is usually shorter than the Reel.  Pad it to the target
        # duration instead of using -shortest, which would otherwise cut the
        # video off as soon as the voice ends.
        audio_index = len(stills)
        command.extend(["-i", audio, "-filter_complex", f"{video_filter};[{audio_index}:a]apad=pad_dur={duration}[a]", "-map", "[v]", "-map", "[a]"])
    else:
        command.extend(["-filter_complex", video_filter, "-map", "[v]", "-an"])
    command.extend(["-t", str(duration), "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path])
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output_path
