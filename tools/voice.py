"""Narration providers for AION videos.

The production workflow uses OpenAI speech so its voice path is the same
authenticated, monitored service family as image production.  Edge TTS stays
available for local development only.
"""

import asyncio
import os


def _openai_speech(text, output_path, speed=None):
    """Write an MP3 from the official OpenAI speech endpoint.

    Do not leave a partial audio file behind when the provider rejects a
    request.  Callers treat False as a real production stop, never a cue to
    silently render a video without narration.
    """
    try:
        import requests

        key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_IMAGE_API_KEY")
        if not key:
            return False
        payload = {
            "model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            "voice": os.getenv("REEL_VOICE", "nova"),
            "input": str(text),
            "response_format": "mp3",
            "instructions": os.getenv(
                "OPENAI_TTS_INSTRUCTIONS",
                "Warm, clear documentary narration. Speak naturally and precisely.",
            ),
        }
        if speed is not None:
            payload["speed"] = round(float(speed), 3)
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if not response.ok or not response.content:
            return False
        with open(output_path, "wb") as audio:
            audio.write(response.content)
        return True
    except Exception:
        return False


def synthesize_thai_voice(text, output_path, attempts=5):
    """Thai-language narration for a dubbed audio track.

    Deliberately independent of REEL_VOICE/REEL_VOICE_PROVIDER (the main
    English narration config) -- a Thai dub must always use a real Thai
    voice regardless of whichever provider/voice the primary pipeline
    happens to be configured with. edge-tts's websocket to Microsoft is
    intermittently flaky -- confirmed twice in real production runs on
    2026-09-27, including a case where 3 attempts with (2,4,6)s backoff
    all failed (each at a different scene) but a later run succeeded --
    so this retries more patiently before giving up, and logs the actual
    exception to stderr on final failure (silently swallowing it, as the
    first version did, left every failure looking identical -- an
    isolated Microsoft outage indistinguishable from a permanent
    misconfiguration like a retired THAI_VOICE name).
    """
    import asyncio
    import sys
    import time

    voice = os.getenv("THAI_VOICE", "th-TH-PremwadeeNeural")
    last_exc = None
    for attempt in range(attempts):
        try:
            import edge_tts

            asyncio.run(edge_tts.Communicate(str(text), voice=voice).save(str(output_path)))
            return True
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(3 * (attempt + 1))
    print(f"synthesize_thai_voice: giving up after {attempts} attempts: {type(last_exc).__name__}: {last_exc}", file=sys.stderr)
    return False


def synthesize_reel_voice(text, output_path, speed=None):
    provider = os.getenv("REEL_VOICE_PROVIDER", "edge-tts").strip().lower()
    if provider == "openai":
        return _openai_speech(text, output_path, speed=speed)
    if provider != "edge-tts":
        return False
    try:
        import edge_tts
        voice = os.getenv("REEL_VOICE", "en-US-AvaMultilingualNeural")
        asyncio.run(edge_tts.Communicate(str(text), voice=voice).save(output_path))
        return True
    except Exception:
        return False
