"""Production rules that keep AION a guide, not the subject of every frame."""


class VisualStoryPolicy:
    """Inspectable creative constraints for new AION productions."""

    VERSION = "short-50-180-fact-first-v5"
    MIN_SCENE_SECONDS = 5
    # Five seconds is the authored storyboard beat.  The renderer may extend
    # that picture interval for a naturally spoken line without changing the
    # approved story plan.
    MAX_SCENE_SECONDS = 5
    MAX_RENDERED_SCENE_SECONDS = 7
    MIN_SHORT_DURATION_SECONDS = 50
    MIN_SHORT_SCENES = 10
    MAX_SHORT_DURATION_SECONDS = 180
    # This is a safety ceiling, not a house style.  The Story, Studio and
    # Quality teams decide an episode's target from the narrative need and
    # later viewer evidence.  AION must never turn an educational story into
    # a permanent foreground mascot.
    MAX_AION_FRAME_SHARE = 0.35
    DEFAULT_AION_FRAME_SHARE = 0.20
    DEFAULT_AION_ROLE = "contextual-guide"
    IDENTITY_VERSION = "aion-animated-documentary-guide-v1"
    # 2026-09-22: switched the channel default from the original warm 3D
    # storytelling identity to a new flat vector, neon-bright house style at
    # the owner's request ("closest match to a flat-vector, neon-bright
    # explainer look, emphasise vivid colour"), then the same day promoted
    # to a glossy 3D neon-diorama variant as the channel's signature look
    # after the owner compared real generated previews of both and asked
    # for 3D neon to be the channel's signature ("3D neon ดีกว่ามั้ย เป็น
    # ลายเซ็นของช่องไปเลย"). See CreatorSceneProduction._style_rule() for
    # the full style_rule text and docs/ai-session-log.md for the
    # request/rationale and both preview comparisons. Both prior defaults
    # remain valid style ids for older/manually-placed episodes -- this only
    # changes what NEW auto-staged episodes use.
    CHANNEL_VISUAL_STYLE = "aion-neon-diorama-3d-v1"
    COLOR_DIRECTION = (
        "Vibrant, optimistic colour with a deliberate focal palette: clear warm highlights, "
        "rich natural local colour, and one restrained cyan AION accent. Preserve readable contrast; "
        "do not use grey wash, neon clutter, or indiscriminate saturation."
    )
    APPROVED_IDENTITY_VERSIONS = {
        IDENTITY_VERSION,
        # Previous default episodes remain valid as historical releases. New
        # storyboards use the more accessible 2D documentary identity.
        "aion-stylized-guide-real-world-v1",
        # A deliberately limited seasonal/locale special.  The visual medium
        # changes, but AION remains a small contextual guide with the same
        # recognizable silver hair, cyan eyes and crystal signature.
        "aion-realistic-profile-with-illustrated-postcard-adaptation-v1",
    }
    IDENTITY_SUMMARY = (
        "AION is a contextual guide, not a fixed mascot: each story may choose its own form and clothing, while the "
        "channel keeps one recognizable Visual DNA—original warm 3D educational storytelling with readable staging, "
        "rounded appealing forms, tactile natural materials and gentle cinematic light."
    )
    # This is a production rule, rather than an aesthetic preference: cyan is
    # AION's small recognition signal, never skin, a full outfit, or the main
    # subject of a frame.  It prevents the retired translucent-blue mascot
    # from silently returning when a storyboard is handed to image production.
    RETIRED_FULL_CYAN_PHRASES = (
        "translucent cyan ai storyteller",
        "translucent-cyan character",
        "cyan humanoid",
        "cyan body",
        "all-blue body",
        "all-blue outfit",
    )

    @classmethod
    def validate_identity_contract(cls, episode):
        """Validate the forward-looking AION appearance contract.

        Kept separately from duration policy so it can protect both Shorts
        and long-form storyboards.  Historical published episodes are not
        rewritten; every newly staged current-policy episode must pass it
        before Studio can request paid scene assets.
        """
        identity = episode.get("visual_identity") or {}
        prohibited = {str(item).strip().lower() for item in identity.get("prohibited") or []}
        combined = " ".join((
            str(episode.get("character") or ""),
            str((episode.get("visual_direction") or {}).get("wardrobe") or ""),
            str(((episode.get("visual_style") or {}).get("aion_deliberation") or {}).get("appearance_choice") or ""),
        )).lower()
        reasons = []
        if not {"all-blue body", "all-blue outfit"}.issubset(prohibited):
            reasons.append("missing-no-full-cyan-identity-contract")
        if any(phrase in combined for phrase in cls.RETIRED_FULL_CYAN_PHRASES[:-2]):
            reasons.append("retired-full-cyan-aion-identity")
        return {"eligible": not reasons, "reasons": reasons}

    @classmethod
    def validate_episode(cls, episode):
        reasons = []
        if episode.get("pacing_policy") != cls.VERSION:
            reasons.append("missing-current-pacing-policy")
        seconds = int(episode.get("scene_seconds") or 0)
        if not cls.MIN_SCENE_SECONDS <= seconds <= cls.MAX_SCENE_SECONDS:
            reasons.append("scene-duration-must-be-5-seconds")
        target_duration = int(episode.get("target_duration_seconds") or 0)
        if not cls.MIN_SHORT_DURATION_SECONDS <= target_duration <= cls.MAX_SHORT_DURATION_SECONDS:
            reasons.append("short-duration-must-be-50-to-180-seconds")
        if len(episode.get("scenes") or []) < cls.MIN_SHORT_SCENES:
            reasons.append("short-must-have-at-least-10-scenes")
        identity = episode.get("visual_identity") or {}
        if identity.get("version") not in cls.APPROVED_IDENTITY_VERSIONS:
            reasons.append("missing-approved-aion-visual-identity")
        identity_contract = cls.validate_identity_contract(episode)
        reasons.extend(identity_contract["reasons"])
        visual = episode.get("visual_direction") or {}
        if visual.get("focus") != "subject-first":
            reasons.append("visual-focus-must-be-subject-first")
        if visual.get("aion_role") != cls.DEFAULT_AION_ROLE:
            reasons.append("aion-role-must-be-contextual-guide")
        frame_share = float(visual.get("aion_frame_share_max") or 0)
        if frame_share > cls.MAX_AION_FRAME_SHARE:
            reasons.append("aion-frame-share-too-large")
        if frame_share > cls.DEFAULT_AION_FRAME_SHARE and not visual.get("aion_presence_rationale"):
            reasons.append("missing-aion-presence-rationale")
        return {"eligible": not reasons, "reasons": reasons, "version": cls.VERSION}

    @classmethod
    def prompt_rules(cls, context, frame_share=None):
        target_share = float(frame_share or cls.DEFAULT_AION_FRAME_SHARE)
        return (
            f"Visual focus: the historical/scientific subject and environment are primary; "
            f"AION is a {cls.DEFAULT_AION_ROLE}, usually at most {int(target_share * 100)}% "
            f"of the frame when present. Wardrobe: {context}. Use a new scene-specific image. "
            f"Colour direction: {cls.COLOR_DIRECTION} "
            "No embedded text, logos, watermark, or celebrity/studio imitation."
        )
