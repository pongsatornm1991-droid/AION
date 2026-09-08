"""Turn cited research evidence into an inspectable AION story brief.

This is intentionally a planning layer, not a text/video generator and not a
publisher.  It makes the hand-off between AION's research loop and its creator
loop explicit: a story may only be proposed when it has enough independent,
traceable evidence for a viewer to check it.
"""

import json

from .learning import ResearchEvidenceStore


class ResearchToStory:
    """Prepare non-publishing creator briefs from persisted evidence."""

    CATEGORY = "story_research_briefs"
    SOURCE = "aion-research-to-story"
    MIN_SOURCES = 2

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _question_fields(entry):
        fields = {"statement": "", "criteria": ""}
        for line in str(entry.get("content") or "").splitlines():
            if line.startswith("Question:"):
                fields["statement"] = line.split(":", 1)[1].strip()
            elif line.startswith("Criteria:"):
                fields["criteria"] = line.split(":", 1)[1].strip()
        return fields

    def _questions_by_id(self):
        return {
            entry.get("id"): self._question_fields(entry)
            for entry in self.memory.all("questions")
            if entry.get("id")
        }

    def _briefs(self):
        briefs = []
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload:
                briefs.append({**payload, "memory_id": entry.get("id"), "timestamp": entry.get("timestamp")})
        return sorted(briefs, key=lambda item: item.get("timestamp", ""), reverse=True)

    def _eligible_groups(self):
        """Return groups with two distinct URLs and meaningful observations."""
        records = ResearchEvidenceStore(self.memory, None)
        groups = {}
        for entry in self.memory.all(ResearchEvidenceStore.CATEGORY):
            parsed = records._parse_entry(entry)
            if not parsed:
                continue
            root_id = str(parsed.get("root_question_id") or "").strip()
            url = str(parsed.get("url") or "").strip()
            observation = str(parsed.get("observation") or "").strip()
            if root_id and url and observation:
                groups.setdefault(root_id, []).append(parsed)
        return groups

    def candidates(self):
        questions = self._questions_by_id()
        candidates = []
        for root_id, records in self._eligible_groups().items():
            distinct = {}
            for record in records:
                distinct.setdefault(record["url"].strip().lower(), record)
            sources = list(distinct.values())
            if len(sources) < self.MIN_SOURCES:
                continue
            question = questions.get(root_id, {})
            candidates.append({
                "root_question_id": root_id,
                "topic": question.get("statement") or "AION research question",
                "completion_criteria": question.get("criteria") or "",
                "sources": sources,
            })
        return sorted(candidates, key=lambda item: (item["topic"], item["root_question_id"]))

    def propose_once(self):
        """Persist one brief if a qualified evidence group has no brief yet.

        The output deliberately contains only source observations, uncertainties,
        and production constraints.  A later drafting step must cite this brief
        rather than treating it as a new factual source.
        """
        existing_roots = {str(item.get("root_question_id") or "") for item in self._briefs()}
        candidate = next((item for item in self.candidates() if item["root_question_id"] not in existing_roots), None)
        if not candidate:
            return {"stage": "waiting-for-qualified-research", "brief": None}

        sources = [{
            "title": item.get("title") or "Untitled source",
            "url": item["url"],
            "source_kind": item.get("source_kind") or "external",
            "observation": item["observation"],
            "evidence_memory_id": item.get("memory_id"),
        } for item in candidate["sources"]]
        topic = candidate["topic"]
        brief = {
            "version": 1,
            "status": "research-ready",
            "root_question_id": candidate["root_question_id"],
            "topic": topic,
            "completion_criteria": candidate["completion_criteria"],
            "source_count": len(sources),
            "sources": sources,
            "creative_direction": {
                "format": "illustrated narrated story",
                "audience": "curious viewers of any age; English-first, optional Thai companion text",
                "aion_presence": "AION must be visibly present in every visual beat as the curious guide.",
                "structure": ["question hook", "what each source supports", "what remains uncertain", "invitation to explore"],
            },
            "unknown_facts": "The evidence may not settle every part of the question; state exactly what the sources do not establish.",
            "cognitive_uncertainties": "AION must distinguish source observations from its own interpretation and avoid generalizing beyond these sources.",
            "publication_rule": "This brief is not permission to publish. A separate reviewed production and publishing action is required.",
        }
        related = [candidate["root_question_id"]] + [item["evidence_memory_id"] for item in sources if item.get("evidence_memory_id")]
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(brief, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=4,
            tags=["creator", "research-grounded", "story-brief"], related=related,
        )
        brief["memory_id"] = saved.get("id")
        return {"stage": "brief-created", "brief": brief}

    def snapshot(self):
        briefs = self._briefs()
        current = next((brief for brief in briefs if brief.get("status") == "research-ready"), None)
        return {
            "status": "research-ready" if current else "waiting-for-evidence",
            "current": current,
            "history_count": len(briefs),
            "eligible_topics": len(self.candidates()),
        }
