"""Inspectable, bounded evolution workspace for AION."""

import json


class EvolutionLab:
    """Shows experiments and proposals without granting unrestricted self-modification."""

    def __init__(self, memory): self.memory = memory

    def _records(self, category):
        try: return self.memory.all(category)
        except (OSError, ValueError, TypeError): return []

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            value = None
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _title(text):
        """Give each recorded proposal a readable label without losing detail."""
        lines = [line.strip("# -•0123456789. \t") for line in str(text or "").splitlines()]
        for index, line in enumerate(lines):
            if line.lower().startswith("ข้อเสนอแนะ"):
                return next((item[:120] for item in lines[index + 1:] if item), "ข้อเสนอพัฒนา")
        return next((line[:120] for line in lines if line), "ข้อเสนอพัฒนา")

    def _proposal_items(self, proposals, reviews, plans, results):
        """Expose the actual proposal text plus its autonomous work state."""
        review_by_proposal = {}
        for review in reviews:
            payload = self._payload(review)
            proposal_id = payload.get("proposal_id")
            if proposal_id:
                review_by_proposal[proposal_id] = payload
        plan_by_proposal = {}
        for plan in plans:
            payload = self._payload(plan)
            proposal_id = payload.get("proposal_id")
            if proposal_id:
                plan_by_proposal[proposal_id] = payload
        result_review_ids = {
            self._payload(result).get("review_id")
            for result in results
            if self._payload(result).get("status") == "evaluated"
        }
        items = []
        for proposal in sorted(proposals, key=lambda item: item.get("timestamp", ""), reverse=True):
            review = review_by_proposal.get(proposal.get("id"), {})
            plan = plan_by_proposal.get(proposal.get("id"), {})
            if review.get("review_id") in result_review_ids or plan.get("status") == "evaluated":
                state, label = "done", "ประเมินผลแล้ว"
            elif plan.get("status") in {"queued", "active"}:
                state, label = "active", "กำลังทดลองอัตโนมัติ"
            elif review.get("status") == "approved-for-experiment":
                state, label = "active", "กำลังสร้างแผนทดลอง"
            else:
                state, label = "waiting", "รอรอบคัดกรองอัตโนมัติ"
            content = str(proposal.get("content") or "")
            items.append({
                "id": proposal.get("id"), "title": self._title(content),
                "detail": content[:1800], "timestamp": proposal.get("timestamp", ""),
                "state": state, "status_label": label,
                "experiment": {
                    "sample_size": plan.get("sample_size"),
                    "method": plan.get("method"),
                    "success_signal": plan.get("success_signal"),
                    "stop_rule": plan.get("stop_rule"),
                } if plan else None,
                "auto_action": (
                    "AION จะคัดกรองและทดลองงานด้านคอนเทนต์/กระบวนการที่วัดผลได้เอง "
                    "โดยไม่ต้องรอปุ่มอนุมัติ"
                ),
                "boundary": (
                    "ข้อเสนอที่แตะโค้ด, รหัสลับ, สิทธิ์บัญชี, เงิน, กฎความปลอดภัย "
                    "หรือการเผยแพร่ที่อยู่นอก Quality Gate จะไม่ดำเนินการเอง"
                ),
            })
        return items

    def snapshot(self):
        proposals = self._records("evolution_proposals") + self._records("self_improvement")
        reviews = self._records("improvement_reviews")
        plans = self._records("content_experiment_plans")
        results = self._records("content_experiment_results")
        experiments = self._records("experiments") + plans
        from brain.scientific_discovery import ScientificDiscoveryLab
        science = ScientificDiscoveryLab(self.memory).snapshot()
        return {
            "status": "active" if proposals or experiments else "ready",
            "proposals": len(proposals), "reviews": len(reviews), "experiments": len(experiments),
            "proposal_items": self._proposal_items(proposals, reviews, plans, results),
            "purpose": "แปลงบทเรียนและปัญหาซ้ำเป็นการทดลองที่วัดผลได้",
            "science": science,
            "boundary": "Lab ออกแบบและทดสอบกระบวนการ/ต้นแบบแบบจำกัดขอบเขตได้ แต่ห้ามสร้างหรือปล่อย AI อิสระใหม่ แก้โค้ด สิทธิ์ รหัสลับ เงิน หรือกฎความปลอดภัยเอง",
        }
