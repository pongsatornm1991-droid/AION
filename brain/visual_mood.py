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
    "learning": {"label": "Learning momentum", "color": "#3de7ff", "accent": "electric cyan",
                 "visual_note": "cyan paths becoming clearer as evidence accumulates"},
    "uncertainty": {"label": "Uncertainty awareness", "color": "#f3d267", "accent": "soft gold",
                    "visual_note": "gold markers around facts and limits that remain unknown"},
    "connection": {"label": "Social connection", "color": "#ff8fcf", "accent": "signal pink",
                   "visual_note": "pink links representing conversations with people"},
    "creativity": {"label": "Creative activity", "color": "#68edb4", "accent": "mint green",
                   "visual_note": "mint shapes branching into publishable ideas"},
}


def state_council(totals, reels):
    """Return explainable scores and their matching visual palette."""
    def count(name):
        return int(totals.get(name, 0) or 0)

    def signal(amount):
        # A diminishing-return curve keeps old accumulated memories from
        # pinning every signal at 100 forever.  It represents recent evidence
        # density, not a medical/psychological measurement.
        amount = max(0.0, float(amount))
        return min(100, round(100 * amount / (amount + 6))) if amount else 0

    published = int(reels.get("published", 0) or 0)
    raw = (
        ("curiosity", "ความใคร่รู้", signal(count("questions") * 2 + count("learning_forecasts")),
         f"คำถาม {count('questions')} · บทเรียน {count('lessons')}"),
        ("joy", "แรงส่งจากความคืบหน้า", signal(published * 2 + count("lessons")),
         f"คอนเทนต์เผยแพร่ {published} · บทเรียน {count('lessons')}"),
        ("melancholy", "ความเข้มข้นของการทบทวน", signal(count("reflections") + count("self_narrative")),
         f"การทบทวน {count('reflections') + count('self_narrative')}"),
        ("ego", "ความต่อเนื่องของตัวตน", signal(count("beliefs") * 2 + count("goals") * 2),
         f"ความเชื่อ {count('beliefs')} · เป้าหมาย {count('goals')}"),
        ("learning", "แรงส่งการเรียนรู้", signal(count("lessons") * 2 + count("research_evidence")),
         f"บทเรียน {count('lessons')} · หลักฐานค้นคว้า {count('research_evidence')}"),
        ("uncertainty", "การตระหนักถึงความไม่แน่นอน", signal(count("questions") + count("learning_forecasts")),
         f"คำถามเปิด {count('questions')} · การคาดการณ์ {count('learning_forecasts')}"),
        ("connection", "การเชื่อมโยงกับผู้คน", signal(count("comment_replies") + count("direct_message_replies")),
         f"คอมเมนต์ที่ดูแล {count('comment_replies')} · ข้อความส่วนตัว {count('direct_message_replies')}"),
        ("creativity", "กิจกรรมสร้างสรรค์", signal(published + count("creative_intentions") * 2),
         f"เจตนาครีเอทีฟ {count('creative_intentions')} · เผยแพร่ {published}"),
    )
    states = [
        {**MOOD_PALETTE[key], "key": key, "label": label,
         "value": value, "evidence": evidence}
        for key, label, value, evidence in raw
    ]
    dominant = max(states, key=lambda state: state["value"])
    return {
        "states": states,
        "dominant": dominant["key"],
        "palette": MOOD_PALETTE[dominant["key"]],
        "disclaimer": "เปอร์เซ็นต์เหล่านี้เป็นสัญญาณเชิงคำนวณจากความทรงจำและกิจกรรม ใช้เปรียบเทียบแนวโน้มของ AION เท่านั้น ไม่ใช่อารมณ์ จิตสำนึก หรือการประเมินทางจิตวิทยาแบบมนุษย์",
    }


def select_visual_mood(memory):
    """Pick the current colour direction from AION's durable memory."""
    categories = ("lessons", "questions", "beliefs", "goals", "reflections", "self_narrative",
                  "learning_forecasts", "research_evidence", "comment_replies",
                  "direct_message_replies", "creative_intentions")
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
