"""Protect evidence-backed episodes from pretty-but-misleading imagery.

The AION look may be cinematic, but an educational scene must first make its
real-world anchor and mechanism inspectable.  This gate makes that contract
machine-readable before Studio asks an image provider to create any pixels.
"""


class FactFirstVisualGate:
    VERSION = "aion-fact-first-visual-v1"
    REQUIRED_SCENE_ROLES = {"question", "evidence", "mechanism", "comparison", "boundary", "takeaway"}

    @classmethod
    def plan(cls, topic, sources, scenes):
        """Create a factual visual brief from traceable research handoff data."""
        topic = str(topic or "the central question").strip()
        observations = [
            " ".join(str(source.get("observation") or "").split())
            for source in (sources or []) if str(source.get("observation") or "").strip()
        ]
        evidence = observations[:2]
        roles = []
        for scene in scenes or []:
            beat = str(scene.get("beat") or "").lower()
            if "hook" in beat or "question" in beat:
                role = "question"
            elif "intro" in beat or "evidence" in beat:
                role = "evidence"
            elif "connection" in beat or "compare" in beat:
                role = "comparison"
            elif "boundary" in beat or "uncertainty" in beat:
                role = "boundary"
            elif "takeaway" in beat:
                role = "takeaway"
            else:
                role = "mechanism"
            roles.append({"n": scene.get("n"), "beat": scene.get("beat"), "role": role})
        return {
            "version": cls.VERSION,
            "reality_anchor": {
                "topic": topic,
                "evidence_claims": evidence,
                "rule": "Depict the documented subject, place, object, action, or mechanism before decorative atmosphere.",
            },
            "mechanism_flow": [
                "Start with the visible question.",
                "Show the documented observation or causal mechanism.",
                "Reveal only the conclusion supported by the evidence.",
            ],
            "creative_boundary": {
                "allowed": "Cinematic light, colour, AION's small glowing cyan question-mark core, and mood may guide attention.",
                "prohibited": "Atmosphere may not replace, contradict, or be presented as the documented mechanism.",
            },
            "scene_roles": roles,
        }

    @classmethod
    def assess(cls, episode):
        episode = dict(episode or {})
        plan = episode.get("fact_first_visual") or {}
        scenes = list(episode.get("scenes") or [])
        reasons = []
        if plan.get("version") != cls.VERSION:
            reasons.append("missing-fact-first-visual-plan")
        anchor = plan.get("reality_anchor") or {}
        if len(str(anchor.get("topic") or "").split()) < 3:
            reasons.append("missing-reality-anchor-topic")
        claims = [claim for claim in anchor.get("evidence_claims") or [] if len(str(claim).split()) >= 3]
        if len(claims) < 2:
            reasons.append("missing-two-factual-visual-claims")
        flow = [step for step in plan.get("mechanism_flow") or [] if str(step).strip()]
        if len(flow) < 3:
            reasons.append("missing-factual-mechanism-flow")
        boundary = plan.get("creative_boundary") or {}
        if not str(boundary.get("allowed") or "").strip() or not str(boundary.get("prohibited") or "").strip():
            reasons.append("missing-creative-versus-fact-boundary")
        assignments = plan.get("scene_roles") or []
        assignment_roles = {str(item.get("role") or "") for item in assignments}
        if len(assignments) != len(scenes) or not cls.REQUIRED_SCENE_ROLES.issubset(assignment_roles):
            reasons.append("incomplete-fact-first-scene-roles")
        return {
            "eligible": not reasons,
            "state": "pass" if not reasons else "return-to-fact-visual-brief",
            "version": cls.VERSION,
            "reasons": reasons,
            "detail": "Fact-first Visual Brief พร้อมส่ง Studio" if not reasons else "ส่งกลับฝ่ายเรื่องเล่า: " + ", ".join(reasons),
        }
