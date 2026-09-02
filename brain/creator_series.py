"""Validation and dashboard snapshot for long-form AION Creator series."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CreatorSeriesRegistry:
    def __init__(self, root=None):
        self.root = Path(root or ROOT)
        self.directory = self.root / "content" / "creator_series"

    def episodes(self):
        result = []
        for path in sorted(self.directory.glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            scenes = item.get("scenes") or []
            seconds = int(item.get("scene_seconds") or 0)
            if not 24 <= len(scenes) <= 60:
                raise ValueError(f"{item.get('id')} must contain 24–60 visual beats.")
            if not 5 <= seconds <= 10:
                raise ValueError(f"{item.get('id')} violates the 5–10 second scene policy.")
            if int(item.get("target_duration_seconds") or 0) != len(scenes) * seconds:
                raise ValueError(f"{item.get('id')} duration does not match its storyboard.")
            if len(item.get("sources") or []) < 2 or any(not source.get("url") for source in item["sources"]):
                raise ValueError(f"{item.get('id')} needs at least two traceable sources.")
            if any(not scene.get("narration") or not scene.get("visual") for scene in scenes):
                raise ValueError(f"{item.get('id')} has an incomplete visual beat.")
            result.append({**item, "file": str(path.relative_to(self.root)).replace("\\", "/")})
        return result

    def snapshot(self):
        return [{
            "id": item["id"], "series": item["series"], "title": item["title"],
            "status": item["status"], "scene_count": len(item["scenes"]),
            "duration_seconds": item["target_duration_seconds"],
            "source_count": len(item["sources"]), "file": item["file"],
        } for item in self.episodes()]
