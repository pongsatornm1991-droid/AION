"""Turn attributed audience outcomes into a cautious Studio handoff."""

import json


class GrowthToStudio:
    CATEGORY = "growth_insights"
    SOURCE = "aion-growth-to-studio"
    MIN_DISTINCT_CONTENT = 3

    def __init__(self, memory):
        self.memory = memory

    def _outcomes(self):
        latest = {}
        for entry in self.memory.all("content_attribution"):
            try:
                value = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if not value.get("content_id") or not value.get("media_id"):
                continue
            latest[value["media_id"]] = value
        grouped = {}
        for value in latest.values():
            grouped.setdefault(value["content_id"], []).append(value)
        return grouped

    @staticmethod
    def _score(items):
        return sum(int(item.get("like_count") or 0) + 3 * int(item.get("comments_count") or 0) for item in items)

    def reflect_once(self):
        grouped = self._outcomes()
        if len(grouped) < self.MIN_DISTINCT_CONTENT:
            return {"stage": "waiting-for-attributed-outcomes", "observed": len(grouped), "required": self.MIN_DISTINCT_CONTENT}
        scores = {content_id: self._score(items) for content_id, items in grouped.items()}
        best_id = max(scores, key=scores.get)
        evidence = {"content_id": best_id, "engagement_signal": scores[best_id], "sample": len(grouped)}
        handoff = {
            "kind": "audience-learning-handoff",
            "status": "evidence-ready",
            "to": ["Story Architect", "Visual Director", "Audience Accessibility Reviewer"],
            "evidence": evidence,
            "recommendation": "ใช้โครงเรื่องของผลงานที่มีสัญญาณตอบรับดีที่สุดเป็นหนึ่งตัวเลือกสำหรับการทดลองครั้งถัดไป โดยยังต้องรักษาความหลากหลาย คุณค่าต่อผู้ชม และ Quality Gate.",
            "uncertainty": "เป็นสัญญาณจากตัวอย่างจำกัดและไม่ได้พิสูจน์ว่าองค์ประกอบใดเป็นสาเหตุของผลตอบรับ.",
        }
        signature = json.dumps(handoff, ensure_ascii=False, sort_keys=True)
        if any(entry.get("content") == signature for entry in self.memory.all(self.CATEGORY)):
            return {"stage": "unchanged", "handoff": handoff}
        saved = self.memory.remember(self.CATEGORY, signature, memory_type="lesson", source=self.SOURCE,
                                     importance=4, tags=["growth", "evidence", "studio-handoff", best_id])
        return {"stage": "handoff-created", "handoff": handoff, "id": saved.get("id")}
