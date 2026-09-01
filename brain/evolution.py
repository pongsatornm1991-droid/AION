"""Evidence-first proposals for improving AION's own operating habits.

This engine deliberately does *not* edit source code, credentials, budgets,
or safety rules.  It turns observed gaps in AION's memory and creative library
into a small, auditable weekly backlog.  A future controlled implementation
agent can take one proposal, test it, and report the result.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from brain.goals import GoalEngine
from brain.metacognition import MetacognitionEngine


class EvolutionEngine:
    CATEGORY = "evolution_proposals"
    COOLDOWN = timedelta(days=7)

    def __init__(self, memory, video_library_path=None):
        self.memory = memory
        default_library = Path(__file__).resolve().parents[1] / "assets" / "content-library" / "aion-core" / "VIDEO_LIBRARY.json"
        self.video_library_path = Path(video_library_path or default_library)

    def _latest(self):
        entries = self.memory.all(self.CATEGORY)
        return max(entries, key=lambda entry: entry.get("timestamp", ""), default=None)

    def _is_due(self, now):
        latest = self._latest()
        if not latest:
            return True
        try:
            timestamp = datetime.strptime(latest["timestamp"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, TypeError, ValueError):
            return True
        return now - timestamp >= self.COOLDOWN

    def _video_count(self):
        try:
            with self.video_library_path.open(encoding="utf-8") as handle:
                return len(json.load(handle).get("videos", []))
        except (OSError, ValueError, TypeError):
            return 0

    def _proposals(self):
        meta = MetacognitionEngine(self.memory).full_report()
        feedback_count = len(self.memory.all("social_feedback"))
        videos = self._video_count()
        active_goals = len(GoalEngine(self.memory).active_goals())
        proposals = []

        if videos < 6:
            proposals.append({
                "priority": "high",
                "area": "creative-library",
                "evidence": f"Only {videos} curated source video(s) are available; the target is six core themes.",
                "experiment": "Create one unused short vertical source video for the next missing theme, then tag it in VIDEO_LIBRARY.json.",
                "success": "The library reaches six theme-distinct videos and the Reel cycle can select them without reuse.",
            })
        if feedback_count == 0:
            proposals.append({
                "priority": "high",
                "area": "audience-learning",
                "evidence": "No social_feedback entries have been recorded yet.",
                "experiment": "Keep the existing feedback cycle running and collect enough real post observations before changing strategy.",
                "success": "At least five feedback records exist, each linked to a post or Reel outcome.",
            })
        for category in meta["memory_quality"]["flagged_low_quality"]:
            proposals.append({
                "priority": "medium",
                "area": "memory-quality",
                "evidence": f"Memory category '{category}' has enough entries to be flagged for low average quality.",
                "experiment": "Improve future records in this category with source, concrete evidence, and related-memory links.",
                "success": "The category is no longer flagged by the next metacognition report.",
            })
        for recurring in meta["recurring_errors"]["recurring"][:2]:
            proposals.append({
                "priority": "medium",
                "area": "recurring-error",
                "evidence": f"Lesson source '{recurring['source']}' recurred {recurring['count']} times.",
                "experiment": "Inspect the named failure source and add one deterministic guard or test before retrying the affected behaviour.",
                "success": "No additional lesson from that source is recorded in the following review period.",
            })
        if active_goals == 0:
            proposals.append({
                "priority": "medium",
                "area": "goal-continuity",
                "evidence": "There are no active goals in AION's current memory.",
                "experiment": "Let the next evidence-backed reflection originate one bounded goal with a concrete completion criterion.",
                "success": "One active goal exists and has an attempt or outcome recorded.",
            })
        return proposals, {"videos": videos, "feedback_records": feedback_count, "active_goals": active_goals}

    @staticmethod
    def _format(proposals, snapshot):
        # MemoryEngine uses a level-two Markdown heading as its on-disk entry
        # separator, so proposal internals intentionally begin at level three.
        lines = ["# AION Evolution Proposal", "", "### Evidence snapshot"]
        lines.extend(f"- {key.replace('_', ' ').title()}: {value}" for key, value in snapshot.items())
        lines.extend(["", "### Proposed experiments"])
        for number, proposal in enumerate(proposals, 1):
            lines.extend([
                f"#### {number}. {proposal['area']} ({proposal['priority']})",
                f"- Evidence: {proposal['evidence']}",
                f"- Next experiment: {proposal['experiment']}",
                f"- Success signal: {proposal['success']}",
                "",
            ])
        lines.extend([
            "### Boundary",
            "These are proposals, not permission to alter source code, secrets, spending limits, safety policy, or social-account permissions.",
        ])
        return "\n".join(lines)

    def propose_once(self, now=None, force=False):
        now = now or datetime.now()
        if not force and not self._is_due(now):
            return {"stage": "not-due", "next_review_after_days": 7}
        proposals, snapshot = self._proposals()
        content = self._format(proposals, snapshot)
        saved = self.memory.remember(
            category=self.CATEGORY,
            content=content,
            memory_type="lesson",
            source="aion-evolution-engine",
            importance=4,
            tags=["evolution", "weekly-review"],
        )
        return {"stage": "proposed", "recorded": saved.get("saved", False), "proposals": proposals, "snapshot": snapshot, "id": saved.get("id")}
