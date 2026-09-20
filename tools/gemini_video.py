"""Automatic image-to-video production through Gemini's Veo API.

This is intentionally a narrow provider adapter: it never publishes, never
logs a credential, and never silently substitutes an old clip when a video
job cannot be completed.  It turns an already-approved scene image plus its
approved visual brief into one short motion source for final assembly.
"""

import os
import time
from pathlib import Path


DEFAULT_MODEL = "veo-3.1-lite-generate-preview"
POLL_SECONDS = 10
MAX_WAIT_SECONDS = 20 * 60


def _api_key():
    return os.getenv("GEMINI_API_KEY", "").strip()


def readiness(environ=None):
    """Return a non-sensitive configuration state for dashboards/preflight."""
    environ = environ if environ is not None else os.environ
    return {
        "configured": bool(str(environ.get("GEMINI_API_KEY") or "").strip()),
        "provider": "gemini-veo",
        "model": str(environ.get("AION_VIDEO_MODEL") or DEFAULT_MODEL).strip(),
        "mode": "automatic-image-to-video",
    }


def generate_scene_video(prompt, source_image, destination, *, aspect_ratio="9:16",
                         model=None, poll_seconds=POLL_SECONDS,
                         max_wait_seconds=MAX_WAIT_SECONDS):
    """Generate a single motion scene and download it to ``destination``.

    Veo jobs are asynchronous.  Polling belongs here so a workflow does not
    need a browser, an owner click, or any provider-specific handoff.
    """
    if not _api_key():
        return {"ok": False, "state": "waiting-for-gemini-video-key"}
    source = Path(source_image)
    target = Path(destination)
    if not source.is_file():
        return {"ok": False, "state": "missing-source-image"}
    try:
        from google import genai
        from google.genai import types
        image_bytes = source.read_bytes()
        mime_type = "image/png" if source.suffix.lower() == ".png" else "image/jpeg"
        client = genai.Client(api_key=_api_key())
        operation = client.models.generate_videos(
            model=(model or os.getenv("AION_VIDEO_MODEL") or DEFAULT_MODEL).strip(),
            prompt=str(prompt),
            image=types.Image(image_bytes=image_bytes, mime_type=mime_type),
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                resolution="720p",
                generate_audio=False,
                person_generation="allow_adult",
            ),
        )
        started = time.monotonic()
        while not operation.done and time.monotonic() - started < max_wait_seconds:
            time.sleep(max(1, int(poll_seconds)))
            operation = client.operations.get(operation)
        if not operation.done:
            return {"ok": False, "state": "provider-timeout", "operation": operation.name}
        response = getattr(operation, "response", None)
        videos = getattr(response, "generated_videos", None) or []
        if not videos:
            return {"ok": False, "state": "provider-returned-no-video", "operation": operation.name}
        target.parent.mkdir(parents=True, exist_ok=True)
        client.files.download(file=videos[0].video, destination=str(target))
        if not target.is_file() or target.stat().st_size == 0:
            return {"ok": False, "state": "download-output-missing", "operation": operation.name}
        return {"ok": True, "state": "completed", "operation": operation.name,
                "path": str(target)}
    except Exception as exc:  # Provider errors stay observable but secret-free.
        return {"ok": False, "state": "provider-failed", "error_type": type(exc).__name__}
