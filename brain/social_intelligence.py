"""Evidence-led Social Intelligence; it observes results, not hype."""

from collections import Counter
import json


class SocialIntelligence:
    """Turn real audience records into bounded content signals."""

    def __init__(self, memory):
        self.memory = memory

    def snapshot(self):
        feedback = self.memory.all("social_feedback")
        published = self.memory.all("published_reels")
        tags = Counter()
        outliers = []
        for item in feedback:
            tags.update(item.get("tags") or [])
            try:
                payload = json.loads(item.get("content") or "{}")
            except (TypeError, ValueError):
                payload = {}
            if not isinstance(payload, dict):
                continue
            views = payload.get("views") or payload.get("view_count")
            followers = payload.get("followers_at_publish") or payload.get("followers_count")
            try:
                if float(views) >= 10 * float(followers) and float(followers) > 0:
                    outliers.append({"title": payload.get("title") or "ผลงานที่มีผลตอบรับสูง", "views": int(float(views)), "followers": int(float(followers))})
            except (TypeError, ValueError):
                continue
        return {
            "name": "Social Intelligence Team",
            "purpose": "วิเคราะห์ผลตอบรับจริง แนวโน้มที่พิสูจน์ได้ และความต่างของแต่ละแพลตฟอร์ม โดยไม่อ้างว่าอะไรไวรัลหากยังไม่มีหลักฐาน",
            "audience_signals": len(feedback),
            "published_records": len(published),
            "emerging_topics": [tag for tag, _ in tags.most_common(5)],
            "outliers": outliers[:5],
            "outlier_state": "พบผลงานที่เกินฐานผู้ติดตาม 10 เท่า" if outliers else "ยังไม่มีข้อมูลยอดชมและฐานผู้ติดตามพอจะตัดสิน outlier",
            "next": "เลือกทดลอง 1 แนวคิดจากผลตอบรับจริง แล้วเปรียบเทียบ retention, comment และ share ตามแพลตฟอร์ม; ใช้มุมใหม่ของ AION ไม่คัดลอกงานต้นทาง",
        }
