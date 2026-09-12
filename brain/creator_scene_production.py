"""Turn a subject-first storyboard into new, auditable scene-image requests."""

import json
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.visual_story_policy import VisualStoryPolicy


class CreatorSceneProduction:
    """Produce a bounded number of missing scene assets per run."""

    def __init__(self, root=None, generator=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.generator = generator

    def _episode(self):
        return next((item for item in CreatorSeriesRegistry(self.root).episodes()
                     if item.get("status") == "storyboard-ready-needs-assets"
                     and item.get("pacing_policy") == VisualStoryPolicy.VERSION), None)

    @staticmethod
    def _safe_name(scene):
        return str(scene.get("beat") or "scene").replace("/", "-").replace(" ", "-")

    def _prompt(self, episode, scene):
        direction = episode.get("visual_direction") or {}
        wardrobe = direction.get("wardrobe") or "context-appropriate practical explorer clothing with subtle cyan details"
        return " ".join((
            "Use case: historical-scene. Asset type: vertical educational video scene.",
            f"Scene: {scene.get('visual')}",
            "AION is a translucent cyan, constellation-lined AI guide with blue eyes; preserve a consistent identity.",
            VisualStoryPolicy.prompt_rules(wardrobe),
            "Composition: vertical 9:16, wide or medium-wide environmental storytelling; AION must be visible but secondary.",
            "Style: original premium family-friendly cinematic 3D illustration.",
            "No words, captions, logos, watermark, UI, or named-studio imitation.",
        ))

    def produce_once(self, limit=3):
        episode = self._episode()
        if episode is None:
            return {"stage": "no-subject-first-storyboard-ready"}
        if self.generator is None:
            from tools.openai_image import generate_scene_image
            generator = generate_scene_image
        else:
            generator = self.generator
        made, failed = [], []
        changed = False
        folder = self.root / "assets" / "content-library" / "aion-stories" / episode["id"]
        folder.mkdir(parents=True, exist_ok=True)
        for scene in episode.get("scenes") or []:
            if len(made) >= limit:
                break
            if scene.get("image"):
                continue
            name = f"{int(scene['n']):02d}-{self._safe_name(scene)}.png"
            destination = folder / name
            if destination.is_file():
                scene["image"] = str(destination.relative_to(self.root)).replace("\\", "/")
                changed = True
                continue
            if generator(self._prompt(episode, scene), str(destination)):
                scene["image"] = str(destination.relative_to(self.root)).replace("\\", "/")
                made.append(scene["n"])
                changed = True
            else:
                failed.append(scene["n"])
                break
        # A missing provider must leave the storyboard byte-for-byte untouched.
        # That makes a failed scheduled run observable instead of looking like work happened.
        if changed:
            source = self.root / episode["file"]
            source.write_text(json.dumps({key: value for key, value in episode.items() if key != "file"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"stage": "scene-assets-produced" if made else "scene-generation-unavailable",
                "episode_id": episode["id"], "produced": made, "failed": failed}
