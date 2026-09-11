"""Validation and dashboard snapshot for long-form AION Creator series."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CreatorSeriesRegistry:
    CREATIVE_DEVICES = {"time-window", "scale-shift", "visual-metaphor", "mystery-reveal", "journey"}
    def __init__(self, root=None):
        self.root = Path(root or ROOT)
        self.directory = self.root / "content" / "creator_series"

    def episodes(self):
        result = []
        for path in sorted(self.directory.glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            scenes = item.get("scenes") or []
            seconds = int(item.get("scene_seconds") or 0)
            episode_format = item.get("format", "long-form-illustrated")
            scene_range = (3, 12) if episode_format == "illustrated-narrated-short" else (24, 60)
            if not scene_range[0] <= len(scenes) <= scene_range[1]:
                raise ValueError(
                    f"{item.get('id')} must contain {scene_range[0]}–{scene_range[1]} visual beats "
                    f"for format {episode_format}."
                )
            if not 5 <= seconds <= 10:
                raise ValueError(f"{item.get('id')} violates the 5–10 second scene policy.")
            if int(item.get("target_duration_seconds") or 0) != len(scenes) * seconds:
                raise ValueError(f"{item.get('id')} duration does not match its storyboard.")
            promise = str(item.get("audience_promise") or "").strip()
            if len(promise) < 20:
                raise ValueError(f"{item.get('id')} needs a clear audience promise, not a posting-only description.")
            hook = str(item.get("wonder_hook") or "").strip()
            if len(hook) < 12:
                raise ValueError(f"{item.get('id')} needs a concrete wonder hook for the opening beat.")
            if item.get("creative_device") not in self.CREATIVE_DEVICES:
                raise ValueError(f"{item.get('id')} needs one declared creative device.")
            age_layers = item.get("age_layers") or {}
            if not isinstance(age_layers, dict) or any(not str(age_layers.get(key) or "").strip() for key in ("children", "family", "deeper")):
                raise ValueError(f"{item.get('id')} needs children, family, and deeper viewing layers.")
            if len(item.get("sources") or []) < 2 or any(not source.get("url") for source in item["sources"]):
                raise ValueError(f"{item.get('id')} needs at least two traceable sources.")
            if any(not scene.get("narration") or not (scene.get("visual") or scene.get("image")) for scene in scenes):
                raise ValueError(f"{item.get('id')} has an incomplete visual beat.")
            if any("aion" not in str(scene.get("visual", "")).lower() for scene in scenes):
                raise ValueError(
                    f"{item.get('id')} must place AION visibly in every visual beat; "
                    "AION is the recurring narrator, not only the voice-over."
                )
            boundary = any(
                str(item.get(key) or "").strip()
                for key in ("science_boundary", "history_boundary", "uncertainty_boundary")
            ) or any(scene.get("beat") in {"boundary", "uncertainty"} for scene in scenes)
            if not boundary:
                raise ValueError(
                    f"{item.get('id')} needs an explicit uncertainty or reconstruction boundary."
                )
            for scene in scenes:
                image = scene.get("image")
                if image and not (self.root / image).is_file():
                    raise ValueError(f"{item.get('id')} references missing image {image}.")
            result.append({**item, "file": str(path.relative_to(self.root)).replace("\\", "/")})
        return result

    def snapshot(self):
        return [{
            "id": item["id"], "series": item["series"], "title": item["title"],
            "status": item["status"], "scene_count": len(item["scenes"]),
            "duration_seconds": item["target_duration_seconds"],
            "source_count": len(item["sources"]), "file": item["file"],
            "audience_promise": item["audience_promise"],
            "has_uncertainty_boundary": True,
            "wonder_hook": item["wonder_hook"],
            "creative_device": item["creative_device"],
        } for item in self.episodes()]
