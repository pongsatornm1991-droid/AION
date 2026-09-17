"""Deterministic editorial preflight for AION storyboards.

It does not predict virality.  It blocks concrete problems that previously
made a finished video confusing: no hook, silent scenes, repeated visual
instructions, or an ending without a viewer takeaway.  VideoQualityGate and
AudioVisualTimingGate remain separate final-media checks.
"""

import re


class WatchabilityGate:
    VERSION = "watchability-v1"

    @staticmethod
    def _normal(value):
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    @classmethod
    def assess_storyboard(cls, episode):
        episode = dict(episode or {})
        scenes = list(episode.get("scenes") or [])
        reasons = []
        hook = scenes[0] if scenes else {}
        if not scenes:
            reasons.append("missing-scenes")
        if len(cls._normal(hook.get("narration"))) < 12:
            reasons.append("hook-is-not-clear-enough")
        if not cls._normal(hook.get("visual")):
            reasons.append("hook-has-no-visual-direction")
        silent = [scene.get("n") for scene in scenes if not cls._normal(scene.get("narration"))]
        if silent:
            reasons.append("silent-storyboard-scenes:" + ",".join(map(str, silent)))
        visuals = [cls._normal(scene.get("visual")) for scene in scenes]
        repeated = sorted({visual for visual in visuals if visual and visuals.count(visual) > 1})
        # A two-minute primary episode can deliberately return to a source
        # while changing the narration's inspection question.  Shorts have
        # no such room: repeated visual direction there is a strong signal of
        # filler and must return to Story.
        if episode.get("format") == "long-form-illustrated":
            repeated = []
        if repeated:
            reasons.append("repeated-visual-direction")
        ending = scenes[-1] if scenes else {}
        if len(cls._normal(ending.get("narration"))) < 12:
            reasons.append("ending-has-no-viewer-takeaway")
        if not episode.get("audience_promise"):
            reasons.append("missing-audience-promise")
        if not episode.get("sources"):
            reasons.append("missing-evidence-sources")
        return {
            "eligible": not reasons,
            "state": "pass" if not reasons else "return-to-story",
            "version": cls.VERSION,
            "reasons": reasons,
            "checks": {
                "hook": "pass" if "hook-is-not-clear-enough" not in reasons and "hook-has-no-visual-direction" not in reasons else "attention",
                "narration_coverage": "pass" if not silent else "attention",
                "visual_variety": "pass" if not repeated else "attention",
                "ending": "pass" if "ending-has-no-viewer-takeaway" not in reasons else "attention",
                "viewer_value": "pass" if episode.get("audience_promise") else "attention",
            },
            "detail": "บทพร้อมส่งผลิต" if not reasons else "ส่งกลับฝ่ายเรื่องเล่า: " + ", ".join(reasons),
        }
