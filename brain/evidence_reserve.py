"""Truthful upstream inventory for the daily Creator Shorts lane.

The release buffer answers "do we have a video ready today?"  This module
answers the earlier, more useful question: "do we have enough independently
grounded ideas to keep making videos next week?"  It never promotes a topic
to evidence-qualified status itself.
"""

import json

from .curiosity import CuriosityEngine
from .content_expansion import ContentExpansionPlanner
from .initiative import AutonomousInitiative
from .research_to_story import ResearchToStory
from .research_story_handoff import ResearchStoryHandoff


class EvidenceReserve:
    """Measure the research inventory ahead of story and media production."""

    QUALIFIED_TARGET = 14
    STORY_TARGET = 10

    def __init__(self, memory):
        self.memory = memory

    def _source_coverage(self):
        """Report observed evidence coverage without pretending it is truth.

        A source count is useful for choosing where to improve retrieval, but
        it is not a quality score and must never override source qualification.
        """
        counts = {}
        for entry in self.memory.all("research_evidence"):
            try:
                record = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            source_kind = str(record.get("source_kind") or "").strip()
            if source_kind:
                counts[source_kind] = counts.get(source_kind, 0) + 1
        return {
            "observed_items": sum(counts.values()),
            "by_source": [
                {"source": source, "accepted_observations": count}
                for source, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "boundary": "Coverage counts accepted observations only; they do not prove a source is correct or rank it above the evidence gate.",
        }

    def snapshot(self):
        curiosity = CuriosityEngine(self.memory)
        research = ResearchToStory(self.memory)
        open_questions = curiosity.open_questions(topic=AutonomousInitiative.RECOVERY_TAG)
        active = [item for item in open_questions if not item.get("budget_exhausted")]
        fast_active = [
            item for item in active
            if AutonomousInitiative.FAST_RECOVERY_TAG in (item.get("tags") or [])
        ]
        nearing_budget = [
            item for item in active
            if int(item.get("attempts") or 0) >= max(0, int(item.get("budget") or 0) - 1)
        ]
        exhausted = [item for item in open_questions if item.get("budget_exhausted")]
        candidates = research.candidates()
        briefs = [
            item for item in research._briefs()
            if item.get("status") == "research-ready"
        ]
        # A brief is fresh production inventory only until Story receives it.
        # Counting every historical brief made the dashboard look supplied even
        # after all of those topics had already been staged, retired, or
        # published under an earlier production policy.
        handed_off_roots = ResearchStoryHandoff(self.memory)._existing_roots()

        # A root question can appear in a few historical records but only
        # represents one usable research package.  Count the durable lineage,
        # not raw memory rows.
        qualified_roots = {
            str(item.get("root_question_id") or "").strip()
            for item in candidates
            if item.get("root_question_id")
        }
        brief_roots = {
            str(item.get("root_question_id") or "").strip()
            for item in briefs
            if item.get("root_question_id")
            and str(item.get("root_question_id") or "").strip() not in handed_off_roots
        }
        historical_brief_roots = {
            str(item.get("root_question_id") or "").strip()
            for item in briefs
            if item.get("root_question_id")
        }
        preserved = [
            entry for entry in self.memory.all(AutonomousInitiative.CATEGORY)
            if AutonomousInitiative.RECOVERY_TAG in (entry.get("tags") or [])
        ]
        targets = {
            "questions": AutonomousInitiative.EVIDENCE_RESERVE_TARGET,
            "qualified_evidence": self.QUALIFIED_TARGET,
            "story_briefs": self.STORY_TARGET,
        }
        counts = {
            "questions": len(active),
            "qualified_evidence": len(qualified_roots),
            "story_briefs": len(brief_roots),
            "historical_story_briefs": len(historical_brief_roots),
            "handed_to_story": len(historical_brief_roots & handed_off_roots),
            "preserved_attempts": len(preserved),
            "fast_lane_questions": len(fast_active),
            "nearing_attempt_limit": len(nearing_budget),
            "exhausted_questions": len(exhausted),
        }
        if counts["qualified_evidence"] < targets["qualified_evidence"]:
            state = "critical"
            next_action = "research distinct reserve questions until two independent sources qualify"
        elif counts["story_briefs"] < targets["story_briefs"]:
            state = "attention"
            next_action = (
                "research and qualify distinct new topics; historical briefs already "
                "handed to Story do not count as new production inventory"
            )
        elif counts["questions"] < targets["questions"]:
            state = "attention"
            next_action = "seed additional evidence-friendly questions before the reserve thins"
        else:
            state = "healthy"
            next_action = "maintain the reserve and rotate completed topics"
        return {
            "state": state,
            "targets": targets,
            "counts": counts,
            "next_action": next_action,
            "content_expansion": ContentExpansionPlanner(self.memory).snapshot(),
            "source_coverage": self._source_coverage(),
            "recovery_sla": {
                "state": "healthy" if fast_active else "attention" if active else "critical",
                "fast_lane_active": len(fast_active),
                "nearing_attempt_limit": len(nearing_budget),
                "exhausted_preserved": len(exhausted),
                "rule": "A recovery question has a finite attempt budget. When it is exhausted, its record remains available for learning but it no longer occupies a live slot; the next recovery run can seed a distinct topic.",
                "next_action": (
                    "research fast-lane mechanism questions in parallel with deep research"
                    if fast_active else
                    "seed a distinct fast-lane question; do not retry an exhausted question as if it were new"
                ),
            },
            "boundary": (
                "A question is not evidence, and evidence is not a publishable video. "
                "Qualified evidence requires independent traceable sources; story briefs "
                "still pass novelty, production, and final Quality Gates."
            ),
        }
