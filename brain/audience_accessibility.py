"""Audience and accessibility checks grounded in AION's own evidence.

This module does not invent retention or claim to know what is trending.  It
reports only recorded platform signals and makes accessibility requirements
visible to the existing Quality Gate before a public upload.
"""

import json


class AudienceAccessibilityGate:
    """Non-fictional audience safeguards attached to each publishing review."""

    def assess(self, payload):
        payload = dict(payload or {})
        review = []
        if not payload.get("viewer_value"):
            review.append("viewer-value-not-stated")
        if not payload.get("uncertainty_boundary"):
            review.append("uncertainty-boundary-not-stated")
        if not payload.get("language"):
            review.append("language-not-labelled")
        return {
            # These are review flags, not a fabricated claim that an
            # automated tool can judge whether every viewer understands it.
            "eligible": True,
            "review": review,
            "subtitle_standard": "Long-form releases require a checked caption track before public release.",
            "scene_pacing_standard": "Short-form scenes should normally change within five seconds unless the story needs a deliberate hold.",
        }


class AudienceAccessibility:
    """Summarise evidence received from connected platforms."""

    def __init__(self, memory):
        self.memory = memory

    def snapshot(self):
        feedback = self.memory.all("social_feedback")
        retention = 0
        for entry in feedback:
            try:
                item = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                item = {}
            if isinstance(item, dict) and any(key in item for key in ("average_watch_duration", "retention", "watch_time")):
                retention += 1
        return {
            "name": "Audience Analytics & Accessibility",
            "purpose": "ใช้สัญญาณผู้ชมจริงเพื่อปรับงานให้เข้าใจง่ายสำหรับหลายวัย และทำให้ข้อจำกัดด้านการเข้าถึงปรากฏก่อนเผยแพร่",
            "feedback_records": len(feedback),
            "retention_records": retention,
            "retention_state": "มีข้อมูลให้วิเคราะห์" if retention else "ยังไม่มี retention จากช่องทางจริง",
            "next": "เมื่อ YouTube ส่งข้อมูล retention แล้วให้เทียบ hook, จังหวะฉาก และคำถามผู้ชม; ก่อนคลิปยาวสาธารณะต้องตรวจ caption track.",
        }
