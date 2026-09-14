"""Turn a subject-first storyboard into new, auditable scene-image requests."""

import json
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.costume_direction import CostumeDirection
from brain.visual_story_policy import VisualStoryPolicy


class CreatorSceneProduction:
    """Produce a bounded number of missing scene assets per run."""

    DEFAULT_BATCH_SIZE = 25
    MAX_SCENES_PER_EPISODE_RUN = 120

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
        wardrobe = CostumeDirection.brief_for(episode, scene)
        aspect = "vertical 9:16" if episode.get("format") == "illustrated-narrated-short" else "widescreen 16:9"
        mentions_aion = "aion" in str(scene.get("visual") or "").lower()
        presence = (
            "AION may appear briefly as a small, contextual guide only if this scene description needs it; "
            "keep the subject, people, evidence, and environment dominant."
            if mentions_aion else
            "Do not include AION in this scene. Let the subject, people, evidence, and environment carry the story."
        )
        return " ".join((
            f"Use case: historical-scene. Asset type: {aspect} educational video scene.",
            f"Scene: {scene.get('visual')}",
            "If AION appears, it is an original gender-neutral AI guide with a small faceted cyan crystal core at the sternum, "
            "subtle constellation accents, warm-ivory and charcoal practical clothing, and no all-blue outfit; preserve this identity.",
            presence,
            VisualStoryPolicy.prompt_rules(wardrobe, direction.get("aion_frame_share_max")),
            f"Composition: {aspect}, wide or medium-wide environmental storytelling; never make AION the hero of the frame.",
            "Style: original premium family-friendly cinematic 3D illustration; never imitate a named studio or franchise.",
            "No words, captions, logos, watermark, UI, or named-studio imitation.",
        ))

    def produce_once(self, limit=DEFAULT_BATCH_SIZE):
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
        completed = all(scene.get("image") for scene in episode.get("scenes") or [])
        if completed and episode.get("status") != "assets-ready-for-assembly":
            episode["status"] = "assets-ready-for-assembly"
            changed = True
        # A missing provider must leave the storyboard byte-for-byte untouched.
        # That makes a failed scheduled run observable instead of looking like work happened.
        if changed:
            source = self.root / episode["file"]
            source.write_text(json.dumps({key: value for key, value in episode.items() if key != "file"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"stage": ("scene-assets-complete" if completed else
                          "scene-assets-produced" if made else "scene-generation-unavailable"),
                "episode_id": episode["id"], "produced": made, "failed": failed}

    def produce_episode(self, batch_size=DEFAULT_BATCH_SIZE,
                        max_scenes=MAX_SCENES_PER_EPISODE_RUN):
        """Finish one approved storyboard in the same run, in recoverable batches.

        Batches limit the blast radius of a provider error; they are not a
        daily throttle. A successful batch immediately starts the next one
        until the storyboard is complete or its declared production ceiling is
        reached. The ceiling prevents an unexpectedly huge storyboard from
        creating unbounded API use.
        """
        batch_size = max(1, int(batch_size))
        max_scenes = max(1, int(max_scenes))
        produced, failures, batches = [], [], 0
        while len(produced) < max_scenes:
            result = self.produce_once(limit=min(batch_size, max_scenes - len(produced)))
            batches += 1
            produced.extend(result.get("produced") or [])
            failures.extend(result.get("failed") or [])
            if result["stage"] == "scene-assets-complete":
                return {"stage": "episode-assets-complete", "episode_id": result.get("episode_id"),
                        "produced": produced, "failed": failures, "batches": batches}
            if not result.get("produced"):
                return {"stage": result["stage"], "episode_id": result.get("episode_id"),
                        "produced": produced, "failed": failures, "batches": batches}
        return {"stage": "episode-production-ceiling-reached", "produced": produced,
                "failed": failures, "batches": batches, "ceiling": max_scenes}
