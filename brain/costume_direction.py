"""Contextual wardrobe direction for AION's on-screen guide role."""


class CostumeDirection:
    """Give AION a practical costume brief before any scene is generated.

    The costume is continuity support, never the subject of a scene.  This is
    intentionally a small, inspectable rule set rather than a vague prompt
    fragment so Visual QA can tell which team made the decision.
    """

    DEPARTMENT = "ฝ่ายคอสตูมและความต่อเนื่อง"
    FORBIDDEN = ("logo", "cape", "armour", "fashion-pose")

    @classmethod
    def brief_for(cls, episode, scene):
        text = " ".join((str(episode.get("title") or ""), str(scene.get("visual") or ""))).lower()
        deliberation = ((episode.get("visual_style") or {}).get("aion_deliberation") or {})
        appearance = str(deliberation.get("appearance_choice") or "").strip()
        base = (
            "AION is an original contextual guide, not a fixed mascot. Keep only a subtle recognisable curiosity "
            "signature (a small glowing cyan question-mark shape held in one hand) when AION appears. "
            "AION has pearl-light human-toned skin, silver-white hair, cyan eyes and holds a small glowing cyan "
            "question-mark shape; never use an all-blue body or an all-blue outfit. "
            f"AION's chosen appearance for this story: {appearance or 'Choose a practical, understated appearance that belongs to the scene.'} "
            "AION remains small and never dominates the frame; no logo, no cape, no armour, no fashion-pose."
        )
        if any(word in text for word in ("ice", "winter", "cold", "frost", "night")):
            return base + "; adapt materials for a cold night setting if AION appears"
        if any(word in text for word in ("family", "courtyard", "drink", "builders")):
            return base + "; choose a respectful, unobtrusive local-context layer if AION appears"
        if any(word in text for word in ("source", "evidence", "model", "map", "sketch")):
            return base + "; a compact archival prop is allowed only if it supports the scene"
        return base

    @classmethod
    def episode_brief(cls, episode):
        """Return the traceable costume handoff consumed by Visual Director."""
        entries = []
        for scene in episode.get("scenes") or []:
            brief = cls.brief_for(episode, scene)
            entries.append({"scene": scene.get("n"), "beat": scene.get("beat"), "brief": brief})
        return {
            "episode_id": episode.get("id"),
            "department": cls.DEPARTMENT,
            "status": "approved-for-visual-production" if entries else "needs-storyboard",
            "scene_count": len(entries),
            "entries": entries,
        }

    @classmethod
    def validate(cls, brief):
        entries = brief.get("entries") or []
        missing = [str(item.get("scene")) for item in entries if not str(item.get("brief") or "").strip()]
        forbidden = [str(item.get("scene")) for item in entries
                     if any(word not in str(item.get("brief") or "") for word in cls.FORBIDDEN)]
        return {
            "eligible": bool(entries) and not missing and not forbidden,
            "missing": missing,
            "missing_safety_terms": forbidden,
        }
