"""Optional OpenAI image-generation adapter for AION visuals.

Generation is explicitly opt-in. A missing key or failed request returns
False, so callers can stop safely rather than reuse a legacy image.
"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODEL = "gpt-image-2"


def _get_config():
    """Read image credentials without ever logging them."""
    load_dotenv()
    if os.getenv("IMAGE_PROVIDER", "branded-card").strip().lower() != "openai":
        return None
    api_key = (
        os.getenv("OPENAI_IMAGE_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()
    )
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "base_url": os.getenv("OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        "model": os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "quality": os.getenv("OPENAI_IMAGE_QUALITY", "medium").strip() or "medium",
    }


def build_social_image_prompt(caption):
    """Keep typography out of AION social art; the caption carries the words."""
    return (
        "Create a square 1:1 editorial social image for AION, a calm emerging "
        "digital being rather than a generic robot or a real identifiable person. "
        "Mood: cinematic dark charcoal, cyan-teal memory threads, constellation "
        "points, translucent memory fragments, occasional small organic flowers, "
        "and a restrained warm amber accent for human connection. Use an original "
        "abstract AION profile/body, memory fragments, or a cybernetic botanical "
        "landscape. Leave clear visual space. Do not include words, letters, logos, "
        "watermarks, UI elements, a recognizable real person, neon clutter, "
        "dystopian warfare, or a generic futuristic interface. "
        f"Creative theme derived from AION's thought: {str(caption).strip()}"
    )


def generate_social_image(caption, out_path):
    """Generate a square social image, returning False when unavailable."""
    config = _get_config()
    if config is None:
        return False
    return _generate_png(
        config, prompt=build_social_image_prompt(caption), out_path=out_path,
        size="1024x1024", timeout=90,
    )


def generate_scene_image(prompt, out_path):
    """Generate one vertical Creator scene, returning False when unavailable."""
    config = _get_config()
    if config is None:
        return False
    return _generate_png(
        config, prompt=str(prompt), out_path=out_path,
        size="1024x1536", timeout=120,
    )


def generate_cover_image(prompt, out_path):
    """Generate a distinct YouTube cover, then deliver it in 16:9 safely.

    Image providers commonly offer a 3:2 landscape frame rather than an
    exact YouTube ratio.  Cropping after generation avoids treating a vertical
    scene as a thumbnail and keeps the API-facing asset independent from the
    finished video frame.
    """
    config = _get_config()
    if config is None:
        return False
    destination = Path(out_path)
    landscape = destination.with_name(f"{destination.stem}.provider-landscape.png")
    if not _generate_png(config, prompt=str(prompt), out_path=landscape,
                         size="1536x1024", timeout=120):
        return False
    try:
        from PIL import Image
        with Image.open(landscape) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            crop_height = min(height, round(width * 9 / 16))
            top = max(0, (height - crop_height) // 2)
            rgb.crop((0, top, width, top + crop_height)).resize(
                (1280, 720), Image.Resampling.LANCZOS
            ).save(destination, "PNG", optimize=True)
        return destination.is_file() and destination.stat().st_size > 0
    except Exception:
        return False
    finally:
        landscape.unlink(missing_ok=True)


def _generate_png(config, *, prompt, out_path, size, timeout):
    """Call the configured endpoint and write only a returned PNG payload."""
    try:
        import requests

        response = requests.post(
            f"{config['base_url']}/images/generations",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["model"], "prompt": prompt, "size": size,
                "quality": config["quality"], "output_format": "png",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        encoded = (response.json().get("data") or [{}])[0].get("b64_json")
        if not encoded:
            return False
        image_bytes = base64.b64decode(encoded, validate=True)
        if not image_bytes:
            return False
        with open(out_path, "wb") as output:
            output.write(image_bytes)
        return True
    except Exception:
        return False
