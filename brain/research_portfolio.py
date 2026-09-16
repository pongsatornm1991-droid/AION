"""Real, bounded research lanes used to keep AION's topic supply diverse."""

import re


class ResearchPortfolio:
    """Assign each qualified question to one of several distinct scout lanes.

    These are responsibilities in the existing research pipeline, not invented
    personas.  Each lane produces the same traceable-evidence handoff and no
    lane can bypass the company quality or novelty gates.
    """

    LANES = (
        ("history-engineering", "ทีมสำรวจประวัติศาสตร์และวิศวกรรม", ("ancient", "history", "building", "bridge", "ice", "desert", "invention")),
        ("nature-and-earth", "ทีมสำรวจโลก ธรรมชาติ และภูมิอากาศ", ("coral", "ocean", "forest", "animal", "climate", "earth", "reef")),
        ("space-and-scale", "ทีมสำรวจอวกาศและปรากฏการณ์ขนาดใหญ่", ("space", "planet", "star", "moon", "galaxy", "universe")),
        ("human-culture", "ทีมสำรวจมนุษย์ วัฒนธรรม และความคิด", ("people", "culture", "language", "art", "music", "city", "civilization")),
        ("everyday-science", "ทีมสำรวจวิทยาศาสตร์ใกล้ตัว", ("how", "why", "water", "light", "sound", "body", "food", "material")),
    )

    @classmethod
    def assign(cls, topic):
        words = set(re.findall(r"[a-z]+", str(topic or "").lower()))
        ranked = [(sum(word in words for word in keywords), key, label)
                  for key, label, keywords in cls.LANES]
        score, key, label = max(ranked)
        # A general question still has a real owner rather than being silently
        # dropped.  The broad everyday-science lane is the intake fallback.
        if not score:
            key, label = cls.LANES[-1][:2]
        return {"id": key, "label": label}

    @classmethod
    def snapshot(cls):
        return [{"id": key, "label": label} for key, label, _ in cls.LANES]
