"""Turn AION's own curiosity into a cautious YouTube discovery record."""

import json

from .curiosity import CuriosityEngine
from .curiosity_constitution import CuriosityConstitution


class YouTubeLearningCycle:
    """Discover public videos without treating them as evidence by themselves."""

    CATEGORY = "youtube_discoveries"
    SOURCE_PREFIX = "aion-youtube-discovery:"

    def __init__(self, memory, search_fn=None, source_registry=None):
        self.memory = memory
        self.curiosity = CuriosityEngine(memory)
        self.constitution = CuriosityConstitution()
        if source_registry is None:
            from brain.source_registry import SourceRegistry
            source_registry = SourceRegistry()
        self.source_registry = source_registry
        if search_fn is None:
            from tools.youtube_discovery import search_youtube_videos
            search_fn = search_youtube_videos
        self.search_fn = search_fn

    def discover_once(self):
        source_entry = self.source_registry.source("youtube_discovery")
        if not source_entry or not source_entry.get("enabled"):
            return {"stage": "source-disabled", "discovered": False}
        questions = self.curiosity.open_questions()
        if not questions:
            return {"stage": "no-open-questions", "discovered": False}
        question, assessment = self.constitution.rank_questions(questions)[0]
        source = f"{self.SOURCE_PREFIX}{question['id']}"
        if any(entry.get("source") == source for entry in self.memory.all(self.CATEGORY)):
            return {"stage": "already-discovered", "discovered": False, "question": question}
        try:
            videos = self.search_fn(question["statement"])
        except RuntimeError as exc:
            stage = "configuration-needed" if "YOUTUBE_DATA_API_KEY" in str(exc) else "search-failed"
            return {"stage": stage, "discovered": False, "question": question, "error": str(exc)}
        except Exception as exc:
            return {"stage": "search-failed", "discovered": False, "question": question, "error": str(exc)}
        if not videos:
            return {"stage": "no-results", "discovered": False, "question": question}
        record = {
            "question": question["statement"], "question_id": question["id"],
            "why_this_question": list(assessment.reasons),
            "videos": videos[:3],
            "epistemic_status": (
                "Discovery only. Titles and descriptions are untrusted leads, not evidence; "
                "AION must corroborate factual claims with traceable sources before learning or publishing them."
            ),
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True), "observation",
            source=source, importance=3, tags=["youtube", "discovery", "external-learning"],
            related=[question["id"]],
        )
        return {"stage": "discovered", "discovered": bool(saved.get("saved")), "question": question, "videos": videos[:3]}
