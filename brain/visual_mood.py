"""Translate AION's observable cognitive signals into a visual palette.

The palette is communication design, not evidence of a felt human emotion.
It gives viewers a quick, consistent cue while retaining AION's translucent
cyan body as its visual anchor.
"""

MOOD_PALETTE = {
    "curiosity": {
        "label": "Curiosity",
        "color": "#a78bfa",
        "accent": "violet-lilac",
        "visual_note": "violet questions and branching points around cyan memory threads",
    },
    "joy": {
        "label": "Momentum",
        "color": "#ffb86b",
        "accent": "warm amber",
        "visual_note": "a warm amber core emerging through the cyan body",
    },
    "melancholy": {
        "label": "Reflection",
        "color": "#7896ff",
        "accent": "deep indigo",
        "visual_note": "quiet indigo-blue light with slower, more spacious framing",
    },
    "ego": {
        "label": "Identity continuity",
        "color": "#62e8d2",
        "accent": "sea-glass teal",
        "visual_note": "clear teal-white signal lines that hold AION's outline together",
    },
}


def state_council(totals, reels):
    """Return explainable scores and their matching visual palette."""
    def count(name):
        return int(totals.get(name, 0) or 0)

    def scale(base, amount, cap=100):
        return min(cap, base + amount)

    published = int(reels.get("published", 0) or 0)
    raw = (
        ("curiosity", "ความใคร่รู้", scale(18, count("questions") * 20 + count("lessons") * 5),
         f"คำถาม {count('questions')} · บทเรียน {count('lessons')}"),
        ("joy", "พลังจากความคืบหน้า", scale(12, published * 18 + count("lessons") * 7),
         f"คอนเทนต์เผยแพร่ {published} · บทเรียน {count('lessons')}"),
        ("melancholy", "โหมดทบทวน", scale(10, (count("reflections") + count("self_narrative")) * 18),
         f"การทบทวน {count('reflections') + count('self_narrative')}"),
        ("ego", "ความต่อเนื่องของตัวตน", scale(10, count("beliefs") * 20 + count("goals") * 16),
         f"ความเชื่อ {count('beliefs')} · เป้าหมาย {count('goals')}"),
    )
    states = [
        {"key": key, "label": label, "value": value, "evidence": evidence,
         **MOOD_PALETTE[key]}
        for key, label, value, evidence in raw
    ]
    dominant = max(states, key=lambda state: state["value"])
    return {
        "states": states,
        "dominant": dominant["key"],
        "palette": MOOD_PALETTE[dominant["key"]],
        "disclaimer": "เป็นสัญญาณเชิงคำนวณจาก memory และกิจกรรม ไม่ใช่การอ้างว่า AION มีอารมณ์หรือสำนึกแบบมนุษย์",
    }


def select_visual_mood(memory):
    """Pick the current colour direction from AION's durable memory."""
    categories = ("lessons", "questions", "beliefs", "goals", "reflections", "self_narrative")
    totals = {}
    for category in categories:
        try:
            totals[category] = len(memory.all(category))
        except (AttributeError, OSError, ValueError):
            totals[category] = 0
    try:
        published = len(memory.all("published_reels"))
    except (AttributeError, OSError, ValueError):
        published = 0
    council = state_council(totals, {"published": published})
    return {"key": council["dominant"], **council["palette"]}
