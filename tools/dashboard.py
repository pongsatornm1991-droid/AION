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
from brain.visual_mood import state_council
from brain.content_registry import CreatorContentRegistry


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


def _brain_map(memory, limit=30):
    """Return only explicit, inspectable links between real memory records."""
    categories = (
        "beliefs", "goals", "questions", "lessons", "reflections",
        "self_narrative", "learning_forecasts", "growth_insights",
        "published_reels", "social_feedback",
    )
    candidates = []
    for category in categories:
        for entry in _entries(memory, category):
            candidates.append((category, entry))
    candidates.sort(
        key=lambda pair: (pair[1].get("importance", 1), pair[1].get("timestamp", "")),
        reverse=True,
    )
    nodes = []
    for category, entry in candidates[:limit]:
        nodes.append({
            "id": f"{category}:{entry.get('id')}",
            "memory_id": entry.get("id"),
            "category": category,
            "label": _short(entry.get("content"), 92),
            "timestamp": entry.get("timestamp"),
            "importance": entry.get("importance", 1),
            "tags": entry.get("tags") or [],
            "related": entry.get("related") or [],
        })

    by_memory_id = {node["memory_id"]: node["id"] for node in nodes}
    edges = set()
    for index, node in enumerate(nodes):
        for related in node["related"]:
            target = by_memory_id.get(related)
            if target:
                edges.add(tuple(sorted((node["id"], target))) + ("explicit",))
        tags = set(node["tags"])
        if not tags:
            continue
        for other in nodes[index + 1:]:
            if tags & set(other["tags"]):
                edges.add(tuple(sorted((node["id"], other["id"]))) + ("shared-tag",))
    return {
        "nodes": nodes,
        "edges": [
            {"source": source, "target": target, "kind": kind}
            for source, target, kind in sorted(edges)
        ],
    }


def _state_council(totals, reels):
    """Observable cognitive signals, never a claim that AION feels emotions."""
    return state_council(totals, reels)


def build_snapshot(memory_root=None):
    """Build the dashboard data without a network call or write operation."""
    configured_root = memory_root or os.getenv("AION_DASHBOARD_MEMORY_ROOT") or os.getenv("AION_MEMORY_ROOT", "memory")
    memory = MemoryEngine(configured_root)
    reels = _reel_summary(memory)
    instagram = _instagram_snapshot(memory)
    categories = [
        "experiences", "lessons", "questions", "goals", "beliefs", "reflections",
        "self_narrative", "learning_forecasts", "growth_insights",
    ]
    totals = {category: len(_entries(memory, category)) for category in categories}
    total_memories = sum(totals.values())
    observed_entries = []
    for category in categories + ["published_reels", "social_feedback"]:
        observed_entries.extend(_entries(memory, category))
    latest_memory = _latest(observed_entries) or {}
    try:
        creator_library = CreatorContentRegistry(memory).snapshot()
    except (OSError, ValueError, TypeError):
        creator_library = []
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_source": {
            "mode": "configured" if os.getenv("AION_DASHBOARD_MEMORY_ROOT") else "local-default",
            "latest_memory_at": latest_memory.get("timestamp"),
        },
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
                "status": "active" if reels["platform_counts"].get("youtube") else "waiting-for-first-short",
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
        "creator_library": creator_library,
        "brain": _brain_map(memory),
        "state_council": _state_council(totals, reels),
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
        if path.startswith("/content/reels/"):
            target = (ROOT / path.lstrip("/")).resolve()
            reels = (ROOT / "content" / "reels").resolve()
            if target.parent == reels and target.is_file() and target.suffix.lower() in (".png", ".mp4"):
                self._send(target.read_bytes(), "image/png" if target.suffix.lower() == ".png" else "video/mp4")
                return
        self._send("Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)


def main():
    port = int(os.getenv("AION_DASHBOARD_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"AION Observatory is live at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
