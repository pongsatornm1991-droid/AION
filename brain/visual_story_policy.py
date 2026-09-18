"""Production rules that keep AION a guide, not the subject of every frame."""


class VisualStoryPolicy:
    """Inspectable creative constraints for new AION productions."""

    VERSION = "short-50-180-subject-first-v3"
    MIN_SCENE_SECONDS = 5
    MAX_SCENE_SECONDS = 5
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
    IDENTITY_VERSION = "aion-stylized-guide-real-world-v1"
    APPROVED_IDENTITY_VERSIONS = {
        IDENTITY_VERSION,
        # A deliberately limited seasonal/locale special.  The visual medium
        # changes, but AION remains a small contextual guide with the same
        # recognizable silver hair, cyan eyes and crystal signature.
        "aion-realistic-profile-with-illustrated-postcard-adaptation-v1",
    }
    IDENTITY_SUMMARY = (
        "Original stylized 3D animated AION guide: silver-white hair, expressive cyan eyes, pearl-light skin, "
        "a small cyan crystal core, and practical ivory, charcoal, and deep-navy field clothing; "
        "a realistic cinematic world is the setting, never an all-blue body or outfit."
    )

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
            "No embedded text, logos, watermark, or celebrity/studio imitation."
        )
