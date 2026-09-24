"""Truthful upstream inventory for the daily Creator Shorts lane.

The release buffer answers "do we have a video ready today?"  This module
answers the earlier, more useful question: "do we have enough independently
grounded ideas to keep making videos next week?"  It never promotes a topic
to evidence-qualified status itself.
"""

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

    def snapshot(self):
        curiosity = CuriosityEngine(self.memory)
        research = ResearchToStory(self.memory)
        open_questions = curiosity.open_questions(topic=AutonomousInitiative.RECOVERY_TAG)
        active = [item for item in open_questions if not item.get("budget_exhausted")]
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
            "boundary": (
                "A question is not evidence, and evidence is not a publishable video. "
                "Qualified evidence requires independent traceable sources; story briefs "
                "still pass novelty, production, and final Quality Gates."
            ),
        }
