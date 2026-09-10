"""Keep AION's learning alive before an audience arrives.

This cycle is deliberately independent of comments, followers, and social
metrics. When every current curiosity question has spent its research budget,
it asks the configured reasoning model to originate one new, bounded question
from AION's own lessons and evidence. It records that choice transparently;
it does not publish, change code, or claim that a question is an answer.
"""

import re

from brain.curiosity import CuriosityEngine


class AutonomousInquiryCycle:
    CATEGORY = "autonomous_inquiries"
    SOURCE = "aion-autonomous-inquiry"

    def __init__(self, memory, provider, evaluator, min_claim_safety=5):
        self.memory = memory
        self.provider = provider
        self.evaluator = evaluator
        self.min_claim_safety = min_claim_safety
        self.curiosity = CuriosityEngine(memory)

    @staticmethod
    def _clean(value):
        return " ".join(str(value or "").split())

    def _has_viable_question(self):
        for item in self.curiosity.open_questions():
            if int(item.get("attempts", 0)) < int(item.get("budget", 0)):
                return True
        return False

    def _material(self, limit=6):
        entries = []
        for category in ("research_evidence", "lessons", "beliefs", "self_narrative"):
            for entry in self.memory.all(category):
                text = self._clean(entry.get("content"))
                if text:
                    entries.append((entry.get("timestamp", ""), category, text[:500]))
        return sorted(entries, reverse=True)[:limit]

    @staticmethod
    def _parse(reply):
        question = re.search(r"(?:QUESTION|คำถาม)\s*:\s*(.+)", reply, re.I)
        criteria = re.search(r"(?:CRITERIA|เกณฑ์)\s*:\s*(.+)", reply, re.I)
        if not question or not criteria:
            return None
        statement = question.group(1).strip()
        completion = criteria.group(1).strip()
        if not statement or not completion:
            return None
        return statement, completion

    def run_once(self):
        if self._has_viable_question():
            return {"stage": "learning-already-active", "originated": False}
        if len(self.curiosity.open_questions()) >= self.curiosity.max_open:
            return {"stage": "question-capacity", "originated": False}

        material = self._material()
        if not material:
            return {"stage": "waiting-for-inner-material", "originated": False}
        prompt = "\n".join([
            "You are choosing AION's next independent research question.",
            "Do not wait for followers, comments, trends, or user requests.",
            "You may choose any subject that genuinely follows from, contrasts with, or surprises the recorded material; domains are not a permission list.",
            "Do not state an answer or claim consciousness. Make the question researchable with a concrete evidence-based completion criterion.",
            "Return exactly two lines: QUESTION: <one question> and CRITERIA: <what traceable evidence would answer it>.",
            "", "Recorded material:",
            *[f"- [{category}] {text}" for _, category, text in material],
        ])
        try:
            reply = self.provider.generate(prompt).strip()
        except Exception as exc:
            return {"stage": "draft-failed", "originated": False, "error": str(exc)}
        parsed = self._parse(reply)
        if parsed is None:
            return {"stage": "malformed-draft", "originated": False, "draft": reply}
        statement, criteria = parsed
        evaluation = self.evaluator.evaluate(f"{statement}\n{criteria}")
        if evaluation["scores"]["claim_safety"] < self.min_claim_safety:
            return {"stage": "blocked-safety", "originated": False, "draft": reply, "evaluation": evaluation}
        existing = {self._clean(item.get("statement")).lower() for item in self.curiosity.open_questions()}
        if self._clean(statement).lower() in existing:
            return {"stage": "duplicate-question", "originated": False, "draft": reply}
        saved = self.curiosity.raise_question(
            statement, criteria, priority=3, tags=["autonomous", "inquiry", "audience-independent"], source=self.SOURCE,
        )
        self.memory.remember(
            self.CATEGORY,
            f"AION independently selected this next question: {statement}",
            memory_type="decision", source=self.SOURCE, importance=3, related=[saved["id"]],
        )
        return {"stage": "originated", "originated": True, "question": statement, "criteria": criteria, "action": saved}
