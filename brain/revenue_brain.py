"""Revenue readiness for AION, without autonomous commerce.

This module is deliberately a planning and measurement layer.  It may propose
an audience-value experiment, but it cannot publish an offer, accept a deal,
create an account, spend money, or move money.
"""

import json


class RevenueBrain:
    CATEGORY = "revenue_opportunities"
    SOURCE = "aion-revenue-brain"

    GUARDRAILS = (
        "No spending, payment account, contract, sponsorship acceptance, or public sales action without the owner's explicit approval.",
        "Only propose offers that follow from useful original work; never buy followers, fake engagement, or scrape people.",
        "Disclose commercial relationships and AI-assisted production where the platform or audience reasonably needs it.",
    )

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _records(self):
        records = []
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload and payload.get("kind"):
                records.append({**payload, "memory_id": entry.get("id"), "timestamp": entry.get("timestamp")})
        return records

    def propose_once(self):
        """Create one bounded, non-commercial first step if it is missing."""
        existing = {item.get("kind") for item in self._records()}
        if "audience-value-validation" in existing:
            return {"stage": "unchanged"}
        proposal = {
            "kind": "audience-value-validation",
            "status": "ready-for-owner-review",
            "title": "ทดสอบคุณค่าก่อนขาย",
            "why": "AION ยังต้องใช้เสียงตอบรับจริงเพื่อพิสูจน์ว่าซีรีส์ใดช่วยผู้ชมได้ ก่อนเสนอสินค้า บริการ หรือสปอนเซอร์.",
            "next_step": "เผยแพร่ซีรีส์ต้นฉบับ 4 ชิ้นที่มีประโยชน์ชัดเจน แล้วเปรียบเทียบการดูต่อ ความคิดเห็น การบันทึก และการแชร์.",
            "success_signal": "พบอย่างน้อยหนึ่งรูปแบบที่มีการตอบรับจริงและมีคำถาม/คำขอให้ทำต่อจากผู้ชม.",
            "owner_required": "การเปิดร้าน รับเงิน ตั้งราคา รับสปอนเซอร์ ใช้งบ หรือเปิดใช้ลิงก์ affiliate.",
            "risk": "อย่าตีความยอดดูครั้งเดียวว่าเป็นความต้องการซื้อ และอย่าส่งเสริมการขายก่อนมีคุณค่าที่พิสูจน์ได้.",
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(proposal, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=4,
            tags=["revenue", "owner-review", "audience-value"],
        )
        return {"stage": "proposed", "proposal": proposal, "id": saved.get("id")}

    def snapshot(self):
        records = self._records()
        published = len(self.memory.all("published_reels"))
        feedback = len(self.memory.all("social_feedback"))
        offers = [item for item in records if item.get("status") not in {"rejected", "paused"}]
        stage = "validate-audience-value" if feedback < 5 else "ready-to-design-offer"
        return {
            "stage": stage,
            "published_work": published,
            "audience_signals": feedback,
            "opportunities": offers[-4:],
            "guardrails": list(self.GUARDRAILS),
            "next": (
                "เก็บผลตอบรับจริงจากคอนเทนต์ต้นฉบับก่อนออกแบบข้อเสนอที่คนยอมจ่าย"
                if feedback < 5 else
                "ออกแบบข้อเสนอขนาดเล็กที่ต่อยอดจากสิ่งที่ผู้ชมตอบรับ แล้วเสนอเจ้าของก่อนเผยแพร่"
            ),
        }
