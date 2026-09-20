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
