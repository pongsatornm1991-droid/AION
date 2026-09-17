"""Create an inspectable directing plan before Studio renders an episode."""


class AionDirector:
    """Turn an evidence storyboard into a compact, subject-first direction brief.

    This is not an image generator and does not invent facts.  It makes the
    creative decisions already present in an approved storyboard visible to
    Visual, Audio and Quality as one shared plan.
    """

    VERSION = "director-plan-v1"

    @classmethod
    def plan(cls, episode):
        scenes = list((episode or {}).get("scenes") or [])
        hook = scenes[0] if scenes else {}
        ending = scenes[-1] if scenes else {}
        return {
            "version": cls.VERSION,
            "creative_promise": episode.get("audience_promise") or "Give viewers one clear, evidence-led answer.",
            "hook": {
                "seconds": int(episode.get("scene_seconds") or 0),
                "narration": hook.get("narration") or "",
                "visual_priority": hook.get("visual") or "",
            },
            "visual_rule": "The real subject and setting lead each scene; AION is a contextual guide, not the foreground subject.",
            "continuity": {
                "aion_role": (episode.get("visual_direction") or {}).get("aion_role"),
                "identity_version": (episode.get("visual_identity") or {}).get("version"),
                "scene_seconds": int(episode.get("scene_seconds") or 0),
            },
            "ending": {
                "narration": ending.get("narration") or "",
                "viewer_reason_to_return": "End with a clear takeaway or an honest next question; never finish with a silent image.",
            },
        }
