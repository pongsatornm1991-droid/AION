"""A bounded, inspectable creative deliberation step for AION Studio.

The model may invent an original visual metaphor for a story.  It may not
invent facts, copy references, override the source package, or publish.  A
deterministic fallback keeps production recoverable when the provider is down.
"""

import json
import re

from brain.aion_visual_director import AionVisualDirector


class AionCreativeDirector:
    VERSION = "aion-creative-deliberation-v1"

    @staticmethod
    def _clean(value, limit=180):
        return " ".join(str(value or "").split())[:limit].strip()

    @classmethod
    def _fallback(cls, topic, episode_format, reason="provider-unavailable"):
        direction = AionVisualDirector.direct(topic, episode_format)
        return {
            "version": cls.VERSION,
            "origin": "bounded-fallback",
            "reason": reason,
            "premise": f"AION explores {cls._clean(topic)} through a {direction['mood']}.",
            "world": direction["world"],
            "mood": direction["mood"],
            "palette_and_material": direction["palette_and_material"],
            "aion_role": "small contextual guide; never the dominant subject",
            "rendering_rule": direction["rendering_rule"],
        }

    @classmethod
    def propose(cls, topic, audience_promise, episode_format="illustrated-narrated-short", provider=None):
        fallback = cls._fallback(topic, episode_format)
        if provider is None:
            return fallback
        prompt = "\n".join((
            "You are AION's creative director. Propose an ORIGINAL visual thoughtscape for one evidence-grounded educational story.",
            "You are not allowed to change facts, add unsupported claims, name or imitate any artist, studio, channel, franchise, character, or existing artwork.",
            "The subject and evidence must lead. AION is a small contextual guide, never a posed hero.",
            "Return JSON only with these keys: premise, world, mood, palette_and_material, aion_role, rendering_rule.",
            "Each field must be concise and usable as an image-production brief. No text in images.",
            f"Topic: {cls._clean(topic)}",
            f"Viewer promise: {cls._clean(audience_promise, 260)}",
            f"Format: {'vertical 9:16' if episode_format == 'illustrated-narrated-short' else 'widescreen 16:9'}",
        ))
        try:
            raw = provider.generate(prompt)
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("creative response is not an object")
            required = ("premise", "world", "mood", "palette_and_material", "aion_role", "rendering_rule")
            result = {key: cls._clean(parsed.get(key)) for key in required}
            if any(not result[key] for key in required):
                raise ValueError("creative response missing required fields")
            unsafe = ("imitate", "copy ", "in the style of", "disney", "pixar", "ghibli")
            if any(term in " ".join(result.values()).lower() for term in unsafe):
                raise ValueError("creative response requested imitation")
            return {"version": cls.VERSION, "origin": "aion-model-deliberation", **result}
        except Exception as exc:
            return cls._fallback(topic, episode_format, reason=f"provider-fallback:{type(exc).__name__}")
