"""Turn a subject-first storyboard into new, auditable scene-image requests."""

import json
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.costume_direction import CostumeDirection
from brain.visual_story_policy import VisualStoryPolicy
from brain.creator_source_integrity import CreatorSourceIntegrity


class CreatorSceneProduction:
    """Produce a bounded number of missing scene assets per run."""

    DEFAULT_BATCH_SIZE = 25
    MAX_SCENES_PER_EPISODE_RUN = 120

    def __init__(self, root=None, generator=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.generator = generator

    def _episode(self, episode_format=None):
        return next((item for item in CreatorSeriesRegistry(self.root).episodes()
                     if item.get("status") == "storyboard-ready-needs-assets"
                     and (not episode_format or item.get("format") == episode_format)
                     and item.get("pacing_policy") in {VisualStoryPolicy.VERSION, "fast-cut-subject-first-v1"}
                     and CreatorSourceIntegrity.assess(item.get("sources"), item.get("topic_key"), "").get("eligible")
                     # Current storyboards must carry the new human-toned
                     # contextual-guide contract before image generation.
                     and (item.get("pacing_policy") != VisualStoryPolicy.VERSION
                          or VisualStoryPolicy.validate_identity_contract(item).get("eligible"))), None)

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
        visual_style = episode.get("visual_style") or {}
        deliberation = visual_style.get("aion_deliberation") or {}
        if visual_style.get("id") == "aion-illustrated-postcard-v1":
            style_rule = (
                "Style: original hand-painted watercolor and gouache illustrated postcard; "
                "soft rainy-season atmosphere, visible paper grain, gentle pigment blooms, "
                "warm everyday Southeast Asian setting, and clear educational visual storytelling. "
                "Do not imitate any named artist, studio, or existing illustration."
            )
        elif visual_style.get("id") == "aion-animated-documentary-v1":
            style_rule = (
                "Style: original premium 2D animated documentary illustration; clean expressive linework, "
                "soft cel shading, cinematic painted depth and textures, friendly intelligent characters, "
                "and a beautiful all-ages educational mood. Do not imitate any named artist, studio, channel, "
                "mascot, franchise, or existing composition."
            )
        elif visual_style.get("id") in {"aion-thoughtscape-director-v1", "aion-original-warm-3d-storytelling-v1"}:
            director = visual_style.get("director") or {}
            style_rule = " ".join((
                "Style: AION Thoughtscape direction for this specific story.",
                f"AION's own premise: {deliberation.get('premise') or ''}",
                f"World: {director.get('world') or 'curiosity-atlas'}.",
                f"Mood: {deliberation.get('mood') or director.get('mood') or 'curious, grounded wonder'}.",
                f"Palette/material: {deliberation.get('palette_and_material') or director.get('palette_and_material') or 'cinematic natural texture'}.",
                str(deliberation.get('rendering_rule') or director.get('rendering_rule') or "Original warm 3D educational storytelling; never imitate a named artist, studio, channel, franchise or existing composition."),
                "Channel Visual DNA must remain original warm 3D educational storytelling: readable staging, rounded appealing forms, tactile natural materials and gentle cinematic light.",
            ))
        else:
            style_rule = (
                "Style: original premium family-friendly cinematic 3D character with photorealistic lighting, material texture and environment; "
                "never imitate a named studio or franchise."
            )
        return " ".join((
            f"Use case: historical-scene. Asset type: {aspect} educational video scene.",
            f"Scene: {scene.get('visual')}",
            "If AION appears, use AION's story-specific chosen presence: "
            f"{deliberation.get('appearance_choice') or 'a subtle cyan curiosity signal or practical contextual guide'}. "
            "Keep AION contextual rather than dominant.",
            presence,
            VisualStoryPolicy.prompt_rules(wardrobe, direction.get("aion_frame_share_max")),
            f"Composition: {aspect}, wide or medium-wide environmental storytelling; never make AION the hero of the frame.",
            style_rule,
            "No words, captions, logos, watermark, UI, or named-studio imitation.",
        ))

    def produce_once(self, limit=DEFAULT_BATCH_SIZE, episode_format=None):
        episode = self._episode(episode_format)
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
            wardrobe = CostumeDirection.brief_for(episode, scene)
            if destination.is_file():
                scene["image"] = str(destination.relative_to(self.root)).replace("\\", "/")
                changed = True
                continue
            if generator(self._prompt(episode, scene), str(destination)):
                scene["image"] = str(destination.relative_to(self.root)).replace("\\", "/")
                # This records the exact approved identity/costume handoff
                # that the image was generated against.  It is not a claim
                # that pixels were vision-reviewed; that remains a separate
                # Quality task instead of silently assuming prompt compliance.
                scene["visual_contract"] = {
                    "identity_version": (episode.get("visual_identity") or {}).get("version", "legacy-unversioned"),
                    "costume_brief": wardrobe,
                }
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
                        max_scenes=MAX_SCENES_PER_EPISODE_RUN, episode_format=None):
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
            result = self.produce_once(limit=min(batch_size, max_scenes - len(produced)), episode_format=episode_format)
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

    def produce_ready_episodes(self, episode_limit=1, batch_size=DEFAULT_BATCH_SIZE,
                               max_scenes=MAX_SCENES_PER_EPISODE_RUN, episode_format=None):
        """Finish a small number of approved storyboards in one Studio shift.

        This is a bounded production shift, not an unbounded content farm:
        every episode still needs a research-grounded storyboard and image
        requests remain capped per episode.  It lets the Tuesday and Wednesday
        shifts build a release buffer rather than making the evening publisher
        wait on a same-day render.
        """
        reports = []
        for _ in range(max(1, int(episode_limit))):
            report = self.produce_episode(batch_size=batch_size, max_scenes=max_scenes, episode_format=episode_format)
            reports.append(report)
            if report.get("stage") != "episode-assets-complete":
                break
        completed = [item.get("episode_id") for item in reports
                     if item.get("stage") == "episode-assets-complete"]
        return {
            "stage": "studio-shift-complete" if completed else reports[-1].get("stage"),
            "completed_episode_ids": completed,
            "reports": reports,
        }
