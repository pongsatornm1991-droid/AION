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
         "luminous marine curiosity", "deep blues, glassy light, living texture and spacious scale"),
        ("ancient-world", ("ancient", "history", "empire", "pyramid", "roman", "persia", "archae"),
         "time-bridge historical wonder", "weathered materials, warm natural light, maps and physical evidence"),
        ("human-everyday", ("people", "human", "community", "food", "home", "school", "street"),
         "tender human observation", "intimate everyday details, soft natural colour and clear human gestures"),
        ("science-lab", ("science", "cell", "brain", "space", "planet", "physics", "biology"),
         "evidence becoming visible", "clean scientific shapes, tactile materials, layered diagrams without embedded text"),
    )

    @classmethod
    def direct(cls, topic, episode_format="illustrated-narrated-short"):
        words = re.sub(r"[^a-z0-9 ]+", " ", str(topic or "").lower())
        selected = next((item for item in cls._WORLDS if any(token in words for token in item[1])), None)
        if selected is None:
            world, mood, palette = ("curiosity-atlas", "a connected world of questions", "twilight warmth, cyan curiosity threads and grounded real textures")
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
            "rendering_rule": "Use original all-ages animated-documentary craft with expressive linework, cinematic painted depth and selective soft cel shading. Never imitate a named artist, studio, channel, franchise or existing composition.",
        }
