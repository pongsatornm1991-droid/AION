"""Turn a subject-first storyboard into new, auditable scene-image requests."""

import json
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.costume_direction import CostumeDirection
from brain.visual_story_policy import VisualStoryPolicy
from brain.creator_source_integrity import CreatorSourceIntegrity
from brain.visual_narrative_gate import VisualNarrativeGate
from brain.fact_first_visual_gate import FactFirstVisualGate


class CreatorSceneProduction:
    """Produce a bounded number of missing scene assets per run."""

    DEFAULT_BATCH_SIZE = 25
    MAX_SCENES_PER_EPISODE_RUN = 120

    def __init__(self, root=None, generator=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.generator = generator

    def _episode(self, episode_format=None):
        return next((item for item in CreatorSeriesRegistry(self.root).episodes()
                     if item.get("status") in {"storyboard-ready-needs-assets", "assets-ready-for-assembly", "production-ready-assets-and-script"}
                     and not self._cover_exists(item)
                     and (not episode_format or item.get("format") == episode_format)
                     and item.get("pacing_policy") in {VisualStoryPolicy.VERSION, "fast-cut-subject-first-v1"}
                     and CreatorSourceIntegrity.assess(item.get("sources"), item.get("topic_key"), "").get("eligible")
                     and (item.get("pacing_policy") != VisualStoryPolicy.VERSION
                          or VisualNarrativeGate.assess(item).get("eligible"))
                     and (item.get("pacing_policy") != VisualStoryPolicy.VERSION
                          or FactFirstVisualGate.assess(item).get("eligible"))
                     # Current storyboards must carry the new human-toned
                     # contextual-guide contract before image generation.
                     and (item.get("pacing_policy") != VisualStoryPolicy.VERSION
                          or VisualStoryPolicy.validate_identity_contract(item).get("eligible"))), None)

    def _cover_path(self, episode):
        return self.root / "content" / "reels" / f"{episode['id']}-cover.png"

    def _cover_exists(self, episode):
        """Whether the on-disk cover already meets the release lane's bar.

        Shorts are composed vertically, so a 9:16 cover is valid evidence
        here too -- this mirrors YouTubeCreatorQueue._cover_quality, the
        check that actually gates release. A long-form episode still
        requires a conventional 16:9 widescreen thumbnail. Without this,
        an already-published Short with a correct vertical cover keeps
        looking "incomplete" here and gets re-selected for production
        forever, starving every other episode behind it in the shift.
        """
        path = self._cover_path(episode)
        try:
            from PIL import Image
            with Image.open(path) as image:
                width, height = image.size
                ratio = width / height if height else 0
                is_short = episode.get("format") == "illustrated-narrated-short"
                is_vertical_short = is_short and abs(ratio - (9 / 16)) <= 0.03 and width >= 720 and height >= 1280
                is_widescreen = width >= 1280 and height >= 720 and abs(ratio - (16 / 9)) <= 0.03
                return is_vertical_short or is_widescreen
        except Exception:
            return False

    @staticmethod
    def _safe_name(scene):
        return str(scene.get("beat") or "scene").replace("/", "-").replace(" ", "-")

    def _style_rule(self, visual_style, deliberation=None):
        deliberation = deliberation or visual_style.get("aion_deliberation") or {}
        style_id = visual_style.get("id")
        if style_id == "aion-neon-vector-shorts-v1":
            return (
                "Style: AION Neon Vector Shorts—an original flat 2D vector explainer illustration, the "
                "channel's boldest, most saturated house style. Simple rounded geometric shapes built from "
                "solid colour with a gentle two-tone gradient for depth, not photoreal shading or texture. "
                "No thick black ink outlines -- shapes separate by colour and value contrast, with at most a "
                "thin same-tone or white edge where needed for readability. This preset's colour direction "
                "REPLACES the channel's usual restrained palette: use a bright, high-contrast, neon-leaning "
                "palette as the dominant colour scheme of every frame -- electric pink/magenta, vivid cobalt "
                "or cyan-blue, saturated orange, and acid green, freely combined against a deep dark or "
                "near-black background so the colours glow. This is deliberate vivid saturation, not "
                "'neon clutter': keep exactly one clear focal mechanism or subject per frame, generous "
                "negative space, and instant one-second readability. Cyan beyond the background palette is "
                "still reserved only for AION's tiny crystal signature, never a full body colour. No text, "
                "logos, watermark, fine texture, grain, photorealism, 3D rendering, or anime, and never "
                "imitate a named artist, studio, channel, mascot or franchise."
            )
        if style_id == "aion-vivid-storyworld-2d-v1":
            return (
                "Style: AION Vivid Storyworld 2D—an original flat editorial science illustration with "
                "clean consistent linework, simplified geometric forms, deliberate paper-grain texture, "
                "large readable colour blocks and only selective atmospheric depth. "
                "Use one dominant object or mechanism per frame. Use deep navy/cobalt for the question, "
                "warm amber for observed evidence, fresh green or coral for the answer, and cyan only "
                "as AION's tiny signature. No photorealism, no 3D rendering, no anime, no clutter, and "
                "never imitate a named artist, studio, channel, mascot or franchise."
            )
        if style_id == "aion-neon-graphic-science-v1":
            return (
                "Style: AION Neon Graphic Science—an original graphic 2.5D science illustration with strong "
                "dark-navy ink outlines, controlled halftone-dot texture, shallow cel-shaded depth, and clean "
                "geometric colour shapes. Use a near-black indigo edge-to-electric-cobalt radial gradient that "
                "brightens only behind the one focal mechanism. Amber represents observed inputs, coral represents "
                "the answer or threshold, fresh green is the subject, and cyan is reserved only for AION's tiny "
                "crystal signature. Where the mechanism itself is electrical, energetic, or signal-like, a "
                "restrained hot-magenta or cyber-yellow neon accent may mark that one specific pulse or moment, "
                "blended into this palette rather than replacing it -- used sparingly on a single element at a "
                "time, never as general scene lighting and never displacing the amber/coral/green/cyan roles "
                "above. Keep the image readable within one second: one mechanism, sparse background, no text, "
                "no logos, no photorealism, no anime, no visual clutter, and never imitate a named artist, "
                "studio, channel, mascot or franchise."
            )
        if style_id == "aion-illustrated-postcard-v1":
            return (
                "Style: original hand-painted watercolor and gouache illustrated postcard; "
                "soft rainy-season atmosphere, visible paper grain, gentle pigment blooms, "
                "warm everyday Southeast Asian setting, and clear educational visual storytelling. "
                "Do not imitate any named artist, studio, or existing illustration."
            )
        if style_id == "aion-animated-documentary-v1":
            return (
                "Style: original premium 2D animated documentary illustration; clean expressive linework, "
                "soft cel shading, cinematic painted depth and textures, friendly intelligent characters, "
                "and a beautiful all-ages educational mood. Do not imitate any named artist, studio, channel, "
                "mascot, franchise, or existing composition."
            )
        if style_id in {"aion-thoughtscape-director-v1", "aion-original-warm-3d-storytelling-v1"}:
            director = visual_style.get("director") or {}
            return " ".join((
                "Style: AION Thoughtscape direction for this specific story.",
                f"AION's own premise: {deliberation.get('premise') or ''}",
                f"World: {director.get('world') or 'curiosity-atlas'}.",
                f"Mood: {deliberation.get('mood') or director.get('mood') or 'curious, grounded wonder'}.",
                f"Palette/material: {deliberation.get('palette_and_material') or director.get('palette_and_material') or 'cinematic natural texture'}.",
                str(deliberation.get('rendering_rule') or director.get('rendering_rule') or "Original warm 3D educational storytelling; never imitate a named artist, studio, channel, franchise or existing composition."),
                "Channel Visual DNA must remain original warm 3D educational storytelling: readable staging, rounded appealing forms, tactile natural materials and gentle cinematic light.",
            ))
        return (
            "Style: original premium family-friendly cinematic 3D character with photorealistic lighting, material texture and environment; "
            "never imitate a named studio or franchise."
        )

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
        fact_plan = episode.get("fact_first_visual") or {}
        fact_anchor = fact_plan.get("reality_anchor") or {}
        fact_boundary = fact_plan.get("creative_boundary") or {}
        deliberation = visual_style.get("aion_deliberation") or {}
        style_rule = self._style_rule(visual_style, deliberation)
        return " ".join((
            f"Use case: historical-scene. Asset type: {aspect} educational video scene.",
            f"Scene: {scene.get('visual')}",
            f"Reality anchor: {fact_anchor.get('rule') or 'Show the documented subject and mechanism first.'}",
            f"Documented claims to preserve: {' | '.join(fact_anchor.get('evidence_claims') or [])}",
            f"Creative boundary: {fact_boundary.get('prohibited') or 'Do not let atmosphere replace the documented mechanism.'}",
            "If AION appears, use AION's story-specific chosen presence: "
            f"{deliberation.get('appearance_choice') or 'a subtle cyan curiosity signal or practical contextual guide'}. "
            "Keep AION contextual rather than dominant.",
            presence,
            VisualStoryPolicy.prompt_rules(wardrobe, direction.get("aion_frame_share_max")),
            f"Composition: {aspect}, wide or medium-wide environmental storytelling; never make AION the hero of the frame.",
            style_rule,
            "No words, captions, logos, watermark, UI, or named-studio imitation.",
        ))

    def _cover_prompt(self, episode):
        """A cover is a separate editorial composition, never a scene crop."""
        visual_style = episode.get("visual_style") or {}
        deliberation = visual_style.get("aion_deliberation") or {}
        direction = episode.get("visual_direction") or {}
        first_scene = (episode.get("scenes") or [{}])[0]
        is_short = episode.get("format") == "illustrated-narrated-short"
        asset_type = "vertical 9:16 cover image" if is_short else "landscape 16:9 cover image"
        style_rule = self._style_rule(visual_style, deliberation)
        # aion-neon-vector-shorts-v1's style_rule already sets its own bold
        # palette and explicitly REPLACES the channel default restrained
        # direction; every other preset keeps the shared colour direction
        # line alongside its own style_rule so a cover still matches its
        # scenes instead of always saying "warm 3D".
        parts = [
            f"Use case: YouTube video thumbnail. Asset type: {asset_type}.",
            f"Story question: {episode.get('wonder_hook') or episode.get('title')}.",
            f"Core visual idea: {episode.get('thumbnail_concept') or first_scene.get('visual') or ''}",
            "Create one instantly understandable, emotionally intriguing focal moment with one clear subject and generous negative space.",
            "This is a standalone cover composition, not a crop or duplicate of any video scene.",
            "The story subject leads; AION appears only if useful and remains a small contextual guide, never a central mascot.",
        ]
        if visual_style.get("id") != "aion-neon-vector-shorts-v1":
            parts.append(f"Colour direction: {VisualStoryPolicy.COLOR_DIRECTION}")
        parts.append(f"Story mood: {deliberation.get('mood') or (visual_style.get('director') or {}).get('mood') or 'curious grounded wonder'}.")
        parts.append(style_rule)
        parts.append("No words, letters, captions, logos, watermark, UI, named artist, studio, franchise, or copied composition.")
        return " ".join(parts)

    def produce_once(self, limit=DEFAULT_BATCH_SIZE, episode_format=None):
        episode = self._episode(episode_format)
        if episode is None:
            return {"stage": "no-subject-first-storyboard-ready"}
        if self.generator is None:
            from tools.openai_image import generate_scene_image
            generator = generate_scene_image
            from tools.openai_image import generate_cover_image
            cover_generator = generate_cover_image
        else:
            generator = self.generator
            # Test and alternative providers receive the same explicit cover
            # brief; production's OpenAI adapter additionally normalises it
            # to a real 16:9 file.
            cover_generator = self.generator
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
        scenes_complete = all(scene.get("image") for scene in episode.get("scenes") or [])
        cover_path = self._cover_path(episode)
        cover_created = False
        if scenes_complete and not self._cover_exists(episode):
            cover_path.parent.mkdir(parents=True, exist_ok=True)
            if cover_generator(self._cover_prompt(episode), str(cover_path)):
                episode["cover_path"] = str(cover_path.relative_to(self.root)).replace("\\", "/")
                episode["cover_contract"] = {
                    "kind": "youtube-custom-thumbnail",
                    "version": "vibrant-subject-first-v1",
                    "prompt_rule": "standalone-cover-not-scene-crop",
                }
                cover_created = True
                changed = True
        completed = scenes_complete and self._cover_exists(episode)
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
                "episode_id": episode["id"], "produced": made, "failed": failed,
                "cover_created": cover_created, "cover_path": str(cover_path.relative_to(self.root)).replace("\\", "/")}

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
