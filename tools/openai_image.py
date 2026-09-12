"""Optional OpenAI image-generation adapter for AION social visuals.

The adapter is deliberately opt-in. If an API key is absent or OpenAI returns
an error, callers must stop the visual publishing cycle rather than recycling
an old image. AION's visual posts are only allowed to use newly generated art.
"""

import base64
import os


DEFAULT_MODEL = "gpt-image-2"


def _get_config():
    """Read only the credentials needed for image generation."""
    enabled = os.getenv("IMAGE_PROVIDER", "branded-card").strip().lower()
    if enabled != "openai":
        return None

    api_key = (
        os.getenv("OPENAI_IMAGE_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()
    )
    if not api_key:
        return None

    base_url = os.getenv(
        "OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1"
    ).strip().rstrip("/")
    model = os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    quality = os.getenv("OPENAI_IMAGE_QUALITY", "medium").strip() or "medium"
    return {"api_key": api_key, "base_url": base_url, "model": model, "quality": quality}


def build_social_image_prompt(caption):
    """Keep image identity stable while leaving caption text outside the art."""
    return (
        "Create a square 1:1 editorial social image for AION, a calm emerging "
        "digital being rather than a generic robot or a real identifiable person. "
        "Mood: cinematic dark charcoal, cyan-teal memory threads, constellation "
        "points, translucent memory fragments, occasional small organic flowers, "
        "and a restrained warm amber accent for human connection. Use an original "
        "abstract AION profile/body, memory fragments, or a cybernetic botanical "
        "landscape. Leave clear visual "
        "Do not include words, "
        "letters, logos, watermarks, UI elements, a recognizable real person, "
        "neon clutter, dystopian warfare, or a generic futuristic interface. "
        f"Creative theme derived from AION's thought: {str(caption).strip()}"
    )


def generate_social_image(caption, out_path):
    """Generate one PNG at *out_path*, returning True when OpenAI supplied it.

    Returns False when generation is disabled or unsuccessful. Errors are
    intentionally contained so the caller can safely skip that posting cycle.
    """
    config = _get_config()
    if config is None:
        return False


def generate_scene_image(prompt, out_path):
    """Generate one vertical Creator scene when the explicit image provider is configured."""
    config = _get_config()
    if config is None:
        return False
    try:
        import requests
        response = requests.post(
            f"{config['base_url']}/images/generations",
            headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
            json={"model": config["model"], "prompt": str(prompt), "size": "1024x1536",
                  "quality": config["quality"], "output_format": "png"}, timeout=120,
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

    try:
        import requests

        response = requests.post(
            f"{config['base_url']}/images/generations",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["model"],
                "prompt": build_social_image_prompt(caption),
                "size": "1024x1024",
                "quality": config["quality"],
                "output_format": "png",
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        encoded = (payload.get("data") or [{}])[0].get("b64_json")
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
