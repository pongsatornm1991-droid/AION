"""Inspectable, bounded evolution workspace for AION."""

import json


class EvolutionLab:
    """Shows experiments and proposals without granting unrestricted self-modification."""

    def __init__(self, memory): self.memory = memory

    def _records(self, category):
        try: return self.memory.all(category)
        except (OSError, ValueError, TypeError): return []

    def snapshot(self):
        proposals = self._records("evolution_proposals") + self._records("self_improvement")
        reviews = self._records("improvement_reviews")
        experiments = self._records("experiments") + self._records("content_experiment_plans")
        return {
            "status": "active" if proposals or experiments else "ready",
            "proposals": len(proposals), "reviews": len(reviews), "experiments": len(experiments),
            "purpose": "แปลงบทเรียนและปัญหาซ้ำเป็นการทดลองที่วัดผลได้",
            "boundary": "Lab ออกแบบและทดสอบกระบวนการ/ต้นแบบแบบจำกัดขอบเขตได้ แต่ห้ามสร้างหรือปล่อย AI อิสระใหม่ แก้โค้ด สิทธิ์ รหัสลับ เงิน หรือกฎความปลอดภัยเอง",
        }
