"""Evidence-led growth requirements for AION Creator episodes.

This is not a promise of virality.  It makes the practical parts of a good
short visible before production: a fast first beat, a reason to keep watching,
an earned reason to follow, and a distinct series angle when real audience
evidence justifies one.
"""


class CreatorGrowthGate:
    """Review a proposed episode without inventing audience results."""

    VERSION = "evidence-led-creator-growth-v1"
    MAX_HOOK_SECONDS = 2

    @classmethod
    def assess(cls, episode):
        episode = dict(episode or {})
        plan = episode.get("growth_plan") or {}
        reasons = []
        if plan.get("version") != cls.VERSION:
            reasons.append("missing-growth-plan")
        if int(plan.get("hook_seconds") or 0) > cls.MAX_HOOK_SECONDS or int(plan.get("hook_seconds") or 0) < 1:
            reasons.append("hook-must-land-within-first-2-seconds")
        if len(str(plan.get("hook_line") or "").split()) < 4:
            reasons.append("hook-line-not-specific-enough")
        if not str(plan.get("retention_promise") or "").strip():
            reasons.append("missing-retention-promise")
        if not str(plan.get("follow_reason") or "").strip():
            reasons.append("missing-follow-reason")
        if not str(plan.get("series_angle") or "").strip():
            reasons.append("missing-series-angle")
        return {
            "eligible": not reasons,
            "reasons": reasons,
            "version": cls.VERSION,
            "principle": "ใช้ข้อมูลผู้ชมจริงเพื่อเลือกหัวข้อ แต่ไม่ลอกฉาก คำพูด หรืออ้างว่าจะไวรัล",
        }

    @classmethod
    def default_plan(cls, topic, audience_promise):
        topic = str(topic or "เรื่องนี้")
        promise = str(audience_promise or "ผู้ชมจะได้คำตอบที่ชัดเจน").strip()
        return {
            "version": cls.VERSION,
            "hook_seconds": cls.MAX_HOOK_SECONDS,
            "hook_line": f"What is the surprising truth about {topic}?",
            "retention_promise": f"แต่ละฉากพาไปสู่คำตอบเดียวที่ชัดเจน: {promise}",
            "follow_reason": "ติดตามเพื่อดูคำถามวิทยาศาสตร์และประวัติศาสตร์เรื่องถัดไปที่เล่าจากหลักฐาน",
            "series_angle": f"อีกมุมหนึ่งของ {topic} จะทำได้เมื่อมีข้อมูลผู้ชมจริงสนับสนุน",
            "editing_rule": "ตัดคำเกริ่น ช่วงเงียบ และภาพที่ไม่พาเรื่องไปข้างหน้า; ทุกฉากต้องเพิ่มข้อมูลหรืออารมณ์ใหม่",
        }
