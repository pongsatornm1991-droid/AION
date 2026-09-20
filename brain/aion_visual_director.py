"""Choose a visual language from a story's subject, not from a fixed special-episode template.

This is a bounded creative director, not an image generator.  It gives Studio
one inspectable, original direction before rendering so a special can be
surprising without becoming visually random or imitating another creator.
"""

import re


class AionVisualDirector:
    VERSION = "aion-thoughtscape-director-v1"

    _WORLDS = (
        ("ocean", ("ocean", "sea", "coral", "octopus", "whale", "reef", "water"),
         "luminous marine curiosity", "vivid reef teal, saturated coral and sunlit caustics balanced with deep blue water"),
        ("ancient-world", ("ancient", "history", "empire", "pyramid", "roman", "persia", "archae"),
         "time-bridge historical wonder", "sun-warmed ochre, lapis, terracotta and verdant accents on tactile weathered materials"),
        ("human-everyday", ("people", "human", "community", "food", "home", "school", "street"),
         "tender human observation", "joyful natural colour, warm sunlight and clear human gestures without a faded filter"),
        ("science-lab", ("science", "cell", "brain", "space", "planet", "physics", "biology"),
         "evidence becoming visible", "crisp cobalt, amber and leaf-green accents on tactile scientific materials; no embedded text"),
    )

    @classmethod
    def direct(cls, topic, episode_format="illustrated-narrated-short"):
        words = re.sub(r"[^a-z0-9 ]+", " ", str(topic or "").lower())
        selected = next((item for item in cls._WORLDS if any(token in words for token in item[1])), None)
        if selected is None:
            world, mood, palette = ("curiosity-atlas", "a connected world of questions", "bright sky blues, warm amber, fresh greens and a small cyan curiosity signal on grounded tactile materials")
        else:
            world, _tokens, mood, palette = selected
        aspect = "vertical 9:16" if episode_format == "illustrated-narrated-short" else "widescreen 16:9"
        return {
            "id": cls.VERSION,
            "world": world,
            "mood": mood,
            "palette_and_material": palette,
            "format": aspect,
            "principle": "AION chooses the world from the subject and emotional promise; evidence and the story lead the frame.",
            "rendering_rule": "Use original all-ages warm 3D educational storytelling with rounded appealing forms, tactile natural materials, gentle cinematic light and a vibrant but controlled focal palette. Never imitate a named artist, studio, channel, franchise or existing composition.",
        }
