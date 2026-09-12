"""Production rules that keep AION a guide, not the subject of every frame."""


class VisualStoryPolicy:
    """Inspectable creative constraints for new AION productions."""

    VERSION = "fast-cut-subject-first-v1"
    MIN_SCENE_SECONDS = 5
    MAX_SCENE_SECONDS = 5
    MAX_AION_FRAME_SHARE = 0.28
    DEFAULT_AION_ROLE = "contextual-guide"

    @classmethod
    def validate_episode(cls, episode):
        reasons = []
        if episode.get("pacing_policy") != cls.VERSION:
            reasons.append("missing-current-pacing-policy")
        seconds = int(episode.get("scene_seconds") or 0)
        if not cls.MIN_SCENE_SECONDS <= seconds <= cls.MAX_SCENE_SECONDS:
            reasons.append("scene-duration-must-be-5-seconds")
        visual = episode.get("visual_direction") or {}
        if visual.get("focus") != "subject-first":
            reasons.append("visual-focus-must-be-subject-first")
        if visual.get("aion_role") != cls.DEFAULT_AION_ROLE:
            reasons.append("aion-role-must-be-contextual-guide")
        if float(visual.get("aion_frame_share_max") or 0) > cls.MAX_AION_FRAME_SHARE:
            reasons.append("aion-frame-share-too-large")
        return {"eligible": not reasons, "reasons": reasons, "version": cls.VERSION}

    @classmethod
    def prompt_rules(cls, context):
        return (
            f"Visual focus: the historical/scientific subject and environment are primary; "
            f"AION is a {cls.DEFAULT_AION_ROLE}, usually at most {int(cls.MAX_AION_FRAME_SHARE * 100)}% "
            f"of the frame. Wardrobe: {context}. Use a new scene-specific image. "
            "No embedded text, logos, watermark, or celebrity/studio imitation."
        )
