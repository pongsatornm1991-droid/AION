"""Turn a research-ready brief into a traceable Story Agent handoff.

This is deliberately a planning step: it creates no media and publishes
nothing.  Its job is to make the Research-to-Story boundary real, inspectable,
and reusable by the Creator Studio.
"""

import json

from brain.research_to_story import ResearchToStory


class ResearchStoryHandoff:
    CATEGORY = "creator_research_handoffs"
    SOURCE = "aion-research-story-handoff"

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _existing_roots(self):
        roots = set()
        for entry in self.memory.all(self.CATEGORY):
            value = self._payload(entry)
            if value and value.get("root_question_id"):
                roots.add(str(value["root_question_id"]))
        return roots

    def create_once(self):
        brief = ResearchToStory(self.memory).snapshot().get("current")
        if not brief:
            return {"stage": "waiting-for-research-brief"}
        root_id = str(brief.get("root_question_id") or "")
        if root_id in self._existing_roots():
            return {"stage": "handoff-already-created", "root_question_id": root_id}

        topic = str(brief.get("topic") or "AION research story")
        handoff = {
            "version": 1,
            "status": "story-ready",
            "root_question_id": root_id,
            "topic": topic,
            "working_title": f"AION Wonders: {topic}",
            "hook": "AION walks into a place that seems impossible — then asks what the evidence actually says.",
            "audience_value": "A viewer of any age can see how careful observation turns a surprising historical or scientific idea into something understandable.",
            "beats": [
                "AION meets the surprising question in a vivid setting.",
                "AION shows what the first source supports.",
                "AION compares the second source rather than repeating the claim.",
                "AION names what remains uncertain and why it matters.",
                "AION closes with one invitation for the viewer to keep wondering.",
            ],
            "source_count": brief.get("source_count", 0),
            "sources": brief.get("sources", []),
            "unknown_facts": brief.get("unknown_facts", "State what the sources do not establish."),
            "cognitive_uncertainties": brief.get("cognitive_uncertainties", "Separate evidence from interpretation."),
            "visual_rule": "AION appears in every beat; create fresh scene-specific imagery and do not use text embedded in Instagram images.",
            "handoff_rule": "Visual and audio production may begin only after this plan passes the existing quality gate.",
        }
        related = [root_id, brief.get("memory_id")] + [item.get("evidence_memory_id") for item in handoff["sources"]]
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(handoff, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=4,
            tags=["creator", "story-handoff", "research-grounded"],
            related=[item for item in related if item],
        )
        handoff["memory_id"] = saved.get("id")
        return {"stage": "story-handoff-created", "handoff": handoff}

    def snapshot(self):
        entries = []
        for entry in self.memory.all(self.CATEGORY):
            value = self._payload(entry)
            if value:
                entries.append({**value, "timestamp": entry.get("timestamp")})
        entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
        return {"current": entries[0] if entries else None, "count": len(entries)}
