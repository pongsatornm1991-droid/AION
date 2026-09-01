"""Local live dashboard for observing AION without altering its memory.

Run with: python tools/dashboard.py
Then open: http://127.0.0.1:8787
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine


DASHBOARD_DIR = ROOT / "dashboard"
DEFAULT_PORT = 8787


def _safe_json(value):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return None


def _entries(memory, category):
    try:
        return memory.all(category)
    except Exception:
        return []


def _latest(entries):
    return max(entries, key=lambda item: item.get("timestamp", ""), default=None)


def _recent(entries, limit=6):
    return sorted(entries, key=lambda item: item.get("timestamp", ""), reverse=True)[:limit]


def _short(text, limit=260):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _reel_summary(memory):
    published = _entries(memory, "published_reels")
    pending = _entries(memory, "pending_reels")
    platform_counts = Counter()
    recent_posts = []
    for entry in published:
        payload = _safe_json(entry.get("content")) or {}
        actions = payload.get("platform_actions") or payload.get("action") or {}
        if actions.get("instagram"):
            platform_counts["instagram"] += 1
        if actions.get("facebook"):
            platform_counts["facebook"] += 1
        if (payload.get("youtube") or {}).get("video_id"):
            platform_counts["youtube"] += 1
        recent_posts.append({
            "timestamp": entry.get("timestamp"),
            "caption": _short(payload.get("caption")),
            "instagram": bool(actions.get("instagram")),
            "facebook": bool(actions.get("facebook")),
            "youtube": bool((payload.get("youtube") or {}).get("video_id")),
        })
    return {
        "published": len(published),
        "pending": len(pending),
        "platform_counts": dict(platform_counts),
        "recent_posts": _recent(recent_posts),
    }


def _instagram_snapshot(memory):
    snapshots = []
    for entry in _entries(memory, "social_feedback"):
        if entry.get("source") != "instagram-feedback":
            continue
        payload = _safe_json(entry.get("content"))
        if payload and payload.get("kind") == "account":
            snapshots.append(payload)
    return _latest(snapshots) or {}


def _thoughts(memory, categories, limit=6):
    entries = []
    for category, label in categories:
        for entry in _entries(memory, category):
            entries.append({
                "category": label,
                "timestamp": entry.get("timestamp"),
                "content": _short(entry.get("content")),
                "importance": entry.get("importance", 1),
            })
    return _recent(entries, limit)


def build_snapshot(memory_root=None):
    """Build the dashboard data without a network call or write operation."""
    memory = MemoryEngine(memory_root or os.getenv("AION_MEMORY_ROOT", "memory"))
    reels = _reel_summary(memory)
    instagram = _instagram_snapshot(memory)
    categories = [
        "experiences", "lessons", "questions", "goals", "beliefs", "reflections",
        "self_narrative", "learning_forecasts", "growth_insights",
    ]
    totals = {category: len(_entries(memory, category)) for category in categories}
    total_memories = sum(totals.values())
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "platforms": {
            "instagram": {
                "status": "connected" if instagram else "waiting-for-metrics",
                "followers": instagram.get("followers_count"),
                "posts": instagram.get("media_count"),
                "reels_published": reels["platform_counts"].get("instagram", 0),
            },
            "facebook": {
                "status": "active" if reels["platform_counts"].get("facebook") else "ready",
                "reels_published": reels["platform_counts"].get("facebook", 0),
            },
            "youtube": {
                "status": "active" if reels["platform_counts"].get("youtube") else "authorization-pending",
                "shorts_published": reels["platform_counts"].get("youtube", 0),
            },
        },
        "mind": {
            "total_memories": total_memories,
            "lessons": totals["lessons"],
            "questions": totals["questions"],
            "goals": totals["goals"],
            "beliefs": totals["beliefs"],
            "reflections": totals["reflections"] + totals["self_narrative"],
            "forecasts": totals["learning_forecasts"],
        },
        "content": reels,
        "thoughts": _thoughts(memory, [
            ("self_narrative", "Inner voice"),
            ("reflections", "Reflection"),
            ("lessons", "Lesson"),
            ("questions", "Question"),
            ("goals", "Goal"),
            ("beliefs", "Belief"),
            ("learning_forecasts", "Forecast"),
            ("growth_insights", "Growth insight"),
        ]),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send(self, body, content_type, status=HTTPStatus.OK):
        encoded = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/snapshot":
            self._send(json.dumps(build_snapshot(), ensure_ascii=False), "application/json; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            self._send((DASHBOARD_DIR / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8")
            return
        self._send("Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)


def main():
    port = int(os.getenv("AION_DASHBOARD_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"AION Observatory is live at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
