"""Validated, idempotent publishing queue for AION Creator episodes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "content" / "creator_library.json"

class CreatorContentRegistry:
    def __init__(self, memory, path=None, root=None):
        self.memory, self.path, self.root = memory, Path(path or DEFAULT_REGISTRY), Path(root or ROOT)

    def episodes(self):
        data = json.loads(self.path.read_text(encoding="utf-8")); policy = data.get("policy") or {}
        minimum, maximum, seen, result = policy.get("scene_min_seconds", 5), policy.get("scene_max_seconds", 10), set(), []
        for raw in data.get("episodes") or []:
            item = dict(raw); key = str(item.get("id") or "").strip()
            scenes, duration = int(item.get("scene_count") or 0), int(item.get("duration_seconds") or 0)
            seconds = duration / scenes if scenes else 0; video = self.root / str(item.get("video_path") or "")
            if not key or key in seen: raise ValueError("Creator episode ids must be present and unique.")
            if not minimum <= seconds <= maximum: raise ValueError(f"{key} violates the 5–10 second scene policy.")
            if not video.is_file() or video.stat().st_size < 100_000: raise ValueError(f"{key} has no usable video.")
            if not str(item.get("caption") or "").strip(): raise ValueError(f"{key} has no caption.")
            seen.add(key); item["seconds_per_scene"] = seconds; result.append(item)
        return result

    def _status_payloads(self):
        values = {"queued": {}, "published": {}}
        for category, state in (("pending_reels", "queued"), ("published_reels", "published")):
            for entry in self.memory.all(category):
                try: payload = json.loads(entry.get("content") or "{}")
                except (TypeError, ValueError): continue
                if payload.get("library_asset"): values[state][str(payload["library_asset"])] = payload
        return values

    def next_ready(self):
        statuses = self._status_payloads(); used = set(statuses["queued"]) | set(statuses["published"])
        return next((item for item in self.episodes() if item["id"] not in used), None)

    def snapshot(self):
        statuses = self._status_payloads(); result = []
        for item in self.episodes():
            status = "published" if item["id"] in statuses["published"] else "queued" if item["id"] in statuses["queued"] else "ready"
            result.append({**item, "status": status})
        return result
