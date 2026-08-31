"""Optional no-key narration for early AION Reels.

This adapter is intentionally best-effort: it uses the `edge-tts` Python
client when enabled and returns False on any network/service issue so a Reel
can safely fall back to its silent caption-led version.
"""

import asyncio
import os


def synthesize_reel_voice(text, output_path):
    if os.getenv("REEL_VOICE_PROVIDER", "edge-tts").strip().lower() != "edge-tts":
        return False
    try:
        import edge_tts
        voice = os.getenv("REEL_VOICE", "en-US-AvaMultilingualNeural")
        asyncio.run(edge_tts.Communicate(str(text), voice=voice).save(output_path))
        return True
    except Exception:
        return False
