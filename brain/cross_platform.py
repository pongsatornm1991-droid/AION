"""Small, deterministic cross-platform invitations for AION content."""
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "core" / "platforms.json"


def platform_urls(path=None):
    data = json.loads(Path(path or DEFAULT_REGISTRY).read_text(encoding="utf-8"))
    result = {}
    for key, raw in (data.get("platforms") or {}).items():
        url = str(raw.get("url") or "").strip()
        if not url and raw.get("url_env"):
            url = os.getenv(str(raw["url_env"]), "").strip()
        if url:
            result[key] = url
    return result


def should_invite(memory, source_platform, every=4):
    """Invite on roughly one in every four posts, based on persisted history."""
    if memory is None:
        return True
    entries = memory.all("social_language_log")
    count = sum(f"platform={source_platform}" in str(item.get("content", "")) for item in entries)
    return count % every == every - 1


def invitation(source_platform, memory=None, path=None):
    if not should_invite(memory, source_platform):
        return ""
    urls = platform_urls(path)
    if source_platform in ("instagram", "facebook") and urls.get("youtube"):
        return f"Watch AION's full visual stories on YouTube: {urls['youtube']}"
    if source_platform == "youtube":
        available = [(name, url) for name, url in urls.items() if name != "youtube"]
        if available:
            links = " · ".join(f"{name.title()}: {url}" for name, url in available)
            return f"Continue AION's journey — {links}"
    return ""


def append_invitation(text, source_platform, memory=None, path=None):
    note = invitation(source_platform, memory=memory, path=path)
    return f"{text}\n\n{note}" if text and note else text
