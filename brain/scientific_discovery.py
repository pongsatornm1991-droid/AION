"""A bounded scientific-method loop for AION's discovery laboratory."""

import json
import uuid


class ScientificDiscoveryLab:
    """Turn a real open question into one falsifiable, traceable protocol.

    This lab does not claim discoveries without evidence and never changes
    source code, credentials, account authority, spending, or safety policy.
    """

    CATEGORY = "scientific_protocols"

    def __init__(self, memory): self.memory = memory

    def _protocols(self):
        output = []
        for entry in self.memory.all(self.CATEGORY):
            try:
                value = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict): output.append(value)
        return output

    def propose_once(self):
        existing = {item.get("question_id") for item in self._protocols() if item.get("status") in {"queued", "researching"}}
        question = next((item for item in self.memory.all("questions") if item.get("id") not in existing), None)
        if not question:
            return {"stage": "no-unassigned-question"}
        statement = str(question.get("content") or "").strip()
        protocol = {
            "protocol_id": uuid.uuid4().hex[:12], "question_id": question.get("id"), "question": statement,
            "status": "queued", "hypothesis": "AION will not treat a hypothesis as a conclusion; evidence may support, weaken, or leave it unresolved.",
            "method": ["define observable claims", "collect at least two independent traceable sources", "compare evidence with the hypothesis", "record uncertainty and replication needs"],
            "success_signal": "A cited result that distinguishes support, contradiction, and unresolved evidence.",
            "boundary": "No human, account, financial, credential, safety-policy, or source-code experiment is performed by this protocol.",
        }
        saved = self.memory.remember(self.CATEGORY, json.dumps(protocol, ensure_ascii=False, sort_keys=True),
                                     memory_type="experiment", source="aion-scientific-discovery-lab", importance=4,
                                     tags=["scientific-method", "queued"], related=[question.get("id")])
        return {"stage": "protocol-created", "protocol": protocol, "memory_id": saved.get("id")}

    def snapshot(self):
        protocols = self._protocols()
        return {"protocols": len(protocols), "queued": sum(item.get("status") == "queued" for item in protocols),
                "purpose": "ตั้งสมมติฐานอย่างถ่อมตน ทดสอบด้วยหลักฐาน และทำซ้ำก่อนสรุป", "roles": ["Theory Scientist", "Evidence Scientist", "Experiment Designer", "Replication Reviewer"],
                "boundary": "ไม่มีการอ้างการค้นพบก่อนมีหลักฐาน และไม่มีการทดลองกับบัญชี เงิน รหัสลับ โค้ดหลัก หรือกฎความปลอดภัย"}
