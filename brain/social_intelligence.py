"""Evidence-led Social Intelligence; it observes results, not hype."""

from collections import Counter


class SocialIntelligence:
    """Turn real audience records into bounded content signals."""

    def __init__(self, memory):
        self.memory = memory

    def snapshot(self):
        feedback = self.memory.all("social_feedback")
        published = self.memory.all("published_reels")
        tags = Counter()
        for item in feedback:
            tags.update(item.get("tags") or [])
        return {
            "name": "Social Intelligence Team",
            "purpose": "วิเคราะห์ผลตอบรับจริง แนวโน้มที่พิสูจน์ได้ และความต่างของแต่ละแพลตฟอร์ม โดยไม่อ้างว่าอะไรไวรัลหากยังไม่มีหลักฐาน",
            "audience_signals": len(feedback),
            "published_records": len(published),
            "emerging_topics": [tag for tag, _ in tags.most_common(5)],
            "next": "เลือกทดลอง 1 แนวคิดจากผลตอบรับจริง แล้วเปรียบเทียบ retention, comment และ share ตามแพลตฟอร์ม",
        }
