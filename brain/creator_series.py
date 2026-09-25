"""Validation and dashboard snapshot for long-form AION Creator series."""
import json
from pathlib import Path

from brain.visual_story_policy import VisualStoryPolicy
from brain.creator_growth import CreatorGrowthGate
from brain.watchability_gate import WatchabilityGate
from brain.visual_narrative_gate import VisualNarrativeGate
from brain.fact_first_visual_gate import FactFirstVisualGate


ROOT = Path(__file__).resolve().parents[1]


class CreatorSeriesRegistry:
    CREATIVE_DEVICES = {"time-window", "scale-shift", "visual-metaphor", "mystery-reveal", "journey"}
    def __init__(self, root=None):
        self.root = Path(root or ROOT)
        self.directory = self.root / "content" / "creator_series"

    def episodes(self, skip_invalid=False):
        """Load and validate every stored episode.

        By default a single malformed episode raises immediately -- this is
        the intentional content quality gate `test_creator_series.py` relies
        on. Automated production scheduling needs the opposite: one storyboard
        that currently fails a policy must not also block every other ready
        episode from being selected. Pass `skip_invalid=True` for that case;
        rejected episodes are collected in `self.invalid` (id, file, reason)
        instead of raising, so the reason stays visible to whatever reads the
        production report.
        """
        result = []
        self.invalid = []
        for path in sorted(self.directory.glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            try:
                self._validate(item)
            except ValueError as exc:
                if not skip_invalid:
                    raise
                self.invalid.append({
                    "id": item.get("id"),
                    "file": str(path.relative_to(self.root)).replace("\\", "/"),
                    "reason": str(exc),
                })
                continue
            result.append({**item, "file": str(path.relative_to(self.root)).replace("\\", "/")})
        return result

    def _validate(self, item):
        scenes = item.get("scenes") or []
        seconds = int(item.get("scene_seconds") or 0)
        episode_format = item.get("format", "long-form-illustrated")
        scene_range = (3, 36) if episode_format == "illustrated-narrated-short" else (24, 120)
        if not scene_range[0] <= len(scenes) <= scene_range[1]:
            raise ValueError(
                f"{item.get('id')} must contain {scene_range[0]}–{scene_range[1]} visual beats "
                f"for format {episode_format}."
            )
        current_policy = item.get("pacing_policy") == VisualStoryPolicy.VERSION
        min_seconds = VisualStoryPolicy.MIN_SCENE_SECONDS if current_policy else 5
        max_seconds = VisualStoryPolicy.MAX_SCENE_SECONDS if current_policy else 10
        if not min_seconds <= seconds <= max_seconds:
            raise ValueError(f"{item.get('id')} violates the {min_seconds}–{max_seconds} second scene policy.")
        if current_policy:
            visual_check = VisualStoryPolicy.validate_episode(item)
            if not visual_check["eligible"]:
                raise ValueError(f"{item.get('id')} violates current visual policy: {', '.join(visual_check['reasons'])}")
            growth_check = CreatorGrowthGate.assess(item)
            if not growth_check["eligible"]:
                raise ValueError(f"{item.get('id')} violates current creator growth policy: {', '.join(growth_check['reasons'])}")
            visual_narrative = VisualNarrativeGate.assess(item)
            if not visual_narrative["eligible"]:
                raise ValueError(f"{item.get('id')} violates visual narrative policy: {', '.join(visual_narrative['reasons'])}")
            fact_visual = FactFirstVisualGate.assess(item)
            if not fact_visual["eligible"]:
                raise ValueError(f"{item.get('id')} violates fact-first visual policy: {', '.join(fact_visual['reasons'])}")
            ending_check = WatchabilityGate.assess_storyboard(item)
            if not ending_check["eligible"]:
                raise ValueError(f"{item.get('id')} violates current watchability policy: {', '.join(ending_check['reasons'])}")
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
                f"{item.get('id')} must place AION in every visual beat; "
                "AION is the recurring guide, not only the voice-over."
            )
        boundary = any(
            str(item.get(key) or "").strip()
            for key in ("science_boundary", "history_boundary", "uncertainty_boundary")
        ) or any(scene.get("beat") in {"boundary", "uncertainty"} for scene in scenes)
        if not boundary:
            raise ValueError(
                f"{item.get('id')} needs an explicit uncertainty or reconstruction boundary."
            )
        # A storyboard intentionally names its future image destinations
        # before Studio generates them.  Treating those paths as an error
        # made a newly approved storyboard crash the dashboard and blocked
        # the very production job meant to create the files.  Once an
        # episode claims to have assets, however, each path remains a hard
        # integrity requirement.
        asset_complete = item.get("status") in {
            "assets-ready-for-assembly",
            "production-ready-assets-and-script",
            "upload-ready",
            "published",
        }
        if asset_complete:
            for scene in scenes:
                image = scene.get("image")
                if image and not (self.root / image).is_file():
                    raise ValueError(f"{item.get('id')} references missing image {image}.")

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
            "scene_seconds": item["scene_seconds"],
            "pacing_policy": item.get("pacing_policy", "legacy-v1"),
            "visual_direction": item.get("visual_direction", {}),
            "visual_style": item.get("visual_style", {}),
            "growth_plan": item.get("growth_plan", {}),
        } for item in self.episodes()]
