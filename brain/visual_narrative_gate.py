"""AION's visual-first story contract.

Inspired by proven science-storytelling discipline, this gate protects a
process rather than copying another channel's artwork: one visual metaphor,
an immediately legible opening, meaningful scene progression, purposeful
colour, an uncluttered cover, and a supporting role for AION.
"""


class VisualNarrativeGate:
    VERSION = "aion-visual-narrative-v1"
    REQUIRED_COLOR_ROLES = {"question", "evidence", "answer", "aion_signature"}

    @classmethod
    def plan(cls, topic, scenes):
        """Create an inspectable direction before images are requested."""
        topic = str(topic or "the central question").strip()
        steps = [str(scene.get("beat") or f"step-{index + 1}")
                 for index, scene in enumerate(scenes or [])]
        return {
            "version": cls.VERSION,
            "visual_metaphor": {
                "statement": f"Follow one visible path of light, evidence, and consequence to understand {topic}.",
                "rule": "Every scene must clarify this one visual idea; it may not introduce a competing metaphor.",
            },
            "opening": {
                "deadline_seconds": 2,
                "visual_question": f"Show the most surprising visible consequence of {topic} before any explanation.",
            },
            "scene_progression": steps,
            "color_roles": {
                "question": "vivid cobalt or deep indigo—what needs explaining",
                "evidence": "warm amber—observed clue or mechanism",
                "answer": "fresh green or coral—resolved relationship or takeaway",
                "aion_signature": "small glowing cyan question-mark held in one hand only; never AION's skin or whole outfit",
            },
            "cover": {
                "primary_focus": topic,
                "rule": "One object or one visible question; generous negative space; no competing details or embedded text.",
            },
            "aion_rule": "AION is a contextual guide, never the subject of every frame.",
        }

    @classmethod
    def assess(cls, episode):
        episode = dict(episode or {})
        plan = episode.get("visual_narrative") or {}
        scenes = list(episode.get("scenes") or [])
        reasons = []
        if plan.get("version") != cls.VERSION:
            reasons.append("missing-visual-narrative-plan")
        metaphor = (plan.get("visual_metaphor") or {}).get("statement")
        if len(str(metaphor or "").split()) < 6:
            reasons.append("missing-single-visual-metaphor")
        opening = plan.get("opening") or {}
        if not str(opening.get("visual_question") or "").strip() or int(opening.get("deadline_seconds") or 99) > 2:
            reasons.append("opening-visual-must-land-within-2-seconds")
        progression = list(plan.get("scene_progression") or [])
        if len(progression) != len(scenes) or len(set(progression)) != len(progression):
            reasons.append("each-scene-needs-a-distinct-story-step")
        colors = plan.get("color_roles") or {}
        if not cls.REQUIRED_COLOR_ROLES.issubset(colors) or any(not str(colors.get(key) or "").strip() for key in cls.REQUIRED_COLOR_ROLES):
            reasons.append("missing-purposeful-color-roles")
        cover = plan.get("cover") or {}
        if not str(cover.get("primary_focus") or "").strip() or "one" not in str(cover.get("rule") or "").lower():
            reasons.append("missing-single-focus-cover-plan")
        direction = episode.get("visual_direction") or {}
        if direction.get("aion_role") != "contextual-guide":
            reasons.append("aion-must-remain-contextual-guide")
        return {
            "eligible": not reasons,
            "state": "pass" if not reasons else "return-to-story",
            "version": cls.VERSION,
            "reasons": reasons,
            "detail": "Visual Narrative พร้อมส่งภาพ" if not reasons else "ส่งกลับฝ่ายเรื่องเล่า: " + ", ".join(reasons),
        }
