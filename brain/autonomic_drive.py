"""An event-aware executive layer for AION's ongoing cognition.

The drive does not make AION wait for an audience or a content calendar. It
reads its current durable state and names the one most valuable next cognitive
act. Workers may then perform that act independently. A checkpointed state
signature makes this event-driven: repeated identical states do not create
fake "thinking" records just because a scheduler heartbeat occurred.
"""

import json

from brain.creator_autonomy import CreatorAutonomy
from brain.curiosity import CuriosityEngine


class AutonomicDrive:
    CATEGORY = "autonomic_drive"
    SOURCE = "aion-autonomic-drive"

    def __init__(self, memory):
        self.memory = memory
        self.curiosity = CuriosityEngine(memory)

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _decision(self):
        questions = self.curiosity.open_questions()
        viable = [q for q in questions if int(q.get("attempts", 0)) < int(q.get("budget", 0))]
        viable.sort(key=lambda q: (q.get("importance", 1), q.get("timestamp", "")), reverse=True)
        # An old evaluator score is a quality signal, not a topic worthy of
        # repeated autonomous research.  Prefer an outward-facing question
        # whenever one exists; otherwise renew direction rather than turning
        # an absence of audience input into endless self-grading.
        external = [q for q in viable if not self._is_self_evaluation_loop(q.get("statement", ""))]
        if external:
            question = external[0]
            return {
                "mode": "research", "focus": question["statement"], "related": question["id"],
                "reason": "AION has an unanswered question with research capacity remaining.",
            }
        if len(questions) < self.curiosity.max_open:
            return {
                "mode": "originate-inquiry", "focus": "Choose a new question from AION's own evidence and lessons.",
                "related": None, "reason": "All current questions are complete for now or exhausted; AION should renew its direction instead of waiting for audience input.",
            }
        intention = CreatorAutonomy(self.memory).pending()
        if intention:
            return {
                "mode": "create", "focus": intention.get("topic", "Current creative intention"),
                "related": intention.get("memory_id"), "reason": "Research is temporarily saturated; turn the current intention into a story or visual draft.",
            }
        return {
            "mode": "reflect", "focus": "Review evidence, lessons, and unresolved tensions.",
            "related": None, "reason": "No immediately executable research item exists; synthesis may reveal the next direction.",
        }

    @staticmethod
    def _is_self_evaluation_loop(statement):
        normalized = str(statement or "").lower()
        markers = (
            "คะแนน", "evaluation", "evaluator", "overall score", "score is", "uncertainty score",
            "uncertainty และ evidence", "คะแนนในหมวด", "เกณฑ์การให้คะแนน",
            "ตอนนี้อยากให้ aion ช่วย", "what would you like aion to help",
        )
        return any(marker in normalized for marker in markers)

    def decide_once(self):
        decision = self._decision()
        signature = json.dumps({key: decision.get(key) for key in ("mode", "focus", "related")}, ensure_ascii=False, sort_keys=True)
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload and payload.get("signature") == signature:
                return {"stage": "unchanged", "decision": payload.get("decision")}
        record = {"signature": signature, "decision": decision}
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=3,
            tags=["autonomy", "executive-drive", decision["mode"]],
            related=[decision["related"]] if decision.get("related") else [],
        )
        return {"stage": "decided", "decision": decision, "action": saved}

    def snapshot(self):
        # A dashboard is an observation surface, not a replay of the last
        # scheduler heartbeat.  Recompute the best next act from current
        # memory so an obsolete self-evaluation task cannot look "active"
        # merely because it was recorded earlier.
        return self._decision()
