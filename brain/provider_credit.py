"""Detect an exhausted OpenAI credit balance before it silently stops production.

2026-10-03: the OpenAI balance ran out and image generation plus the narration
timing check (OpenAI speech) failed on every run for two days. Nothing said so
-- each workflow just reported a generic failure and a "buffer 0/14" -- until
the cause was read out of a run annotation. The provider's own health check
only confirms a key is *configured*, never that it can still spend.

The probe asks for one character of speech: a fraction of a cent, no side
effects, and it fails with the same billing error real production hits.
"""

import os

EXHAUSTED_CODES = {"insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached"}
ENDPOINT = "https://api.openai.com/v1/audio/speech"


def _post(key, payload):
    import requests

    return requests.post(
        ENDPOINT, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload, timeout=20,
    )


def probe_openai_credit(key=None, post=None):
    """Return {"state": "ok" | "exhausted" | "unknown", "detail": ...}. Never raises."""
    key = key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_IMAGE_API_KEY")
    if not key:
        return {"state": "unknown", "detail": "no OpenAI key configured in this run"}
    payload = {
        "model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "voice": os.getenv("REEL_VOICE", "nova"),
        "input": ".", "response_format": "mp3",
    }
    try:
        response = (post or _post)(key, payload)
    except Exception as exc:
        return {"state": "unknown", "detail": f"probe failed: {type(exc).__name__}"}
    if getattr(response, "status_code", 0) < 400:
        return {"state": "ok", "detail": "speech request accepted"}
    try:
        error = (response.json() or {}).get("error") or {}
    except Exception:
        error = {}
    code = str(error.get("code") or error.get("type") or "")
    if code in EXHAUSTED_CODES:
        return {"state": "exhausted", "detail": f"HTTP {response.status_code} {code}"}
    return {"state": "unknown", "detail": f"HTTP {response.status_code} {code}".strip()}
