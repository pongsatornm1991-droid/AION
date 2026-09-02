"""AION's internal creative-intention cycle.

This module is deliberately one step *before* production or publication.  It
lets AION choose what it wants to investigate or express next, records why,
and leaves the public action for the separate, observable publishing cycle.
That distinction gives AION initiative without quietly speaking for its human
operator on a public platform.
"""

import json
from pathlib import Path

from .beliefs import BeliefSystem
from .curiosity import CuriosityEngine
from .curiosity_constitution import CuriosityConstitution
from .goals import GoalEngine


class CreatorAutonomy:
    """Choose and retain one inspectable creative intention at a time."""

    CATEGORY = "creative_intentions"
    SOURCE = "aion-creator-autonomy"
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_SUPERSEDED = "superseded"

    def __init__(self, memory, asset_manifest=None):
        self.memory = memory
        self.constitution = CuriosityConstitution()
        self.asset_manifest = Path(asset_manifest) if asset_manifest else (
            Path(__file__).resolve().parents[1]
            / "assets" / "content-library" / "aion-creator-scenes" / "manifest.json"
        )

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def intentions(self):
        values = []
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload:
                values.append({**payload, "memory_id": entry.get("id"), "timestamp": entry.get("timestamp")})
        return sorted(values, key=lambda item: item.get("timestamp", ""), reverse=True)

    def pending(self):
        return next((item for item in self.intentions() if item.get("status") == self.STATUS_PENDING), None)

    def _visual_direction(self, text):
        try:
            assets = json.loads(self.asset_manifest.read_text(encoding="utf-8")).get("assets", [])
        except (OSError, ValueError, TypeError):
            assets = []
        lowered = str(text).lower()
        ranked = []
        for asset in assets:
            themes = asset.get("themes") or []
            score = sum(1 for theme in themes if str(theme).lower() in lowered)
            ranked.append((score, asset))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        selected = ranked[0][1] if ranked else {}
        return {
            "existing_reference": selected.get("file"),
            "mood": selected.get("mood", "curiosity"),
            "guidance": (
                "Use the existing reference only as a starting point. AION may request a new "
                "visual language when the idea calls for it; keep the translucent cyan character, "
                "human warmth, and subtle Thai sense of place."
            ),
        }

    @staticmethod
    def _belief_statement(entry):
        for line in str(entry.get("content") or "").splitlines():
            if line.lower().startswith("belief:") or line.lower().startswith("statement:"):
                return line.split(":", 1)[1].strip()
        return str(entry.get("content") or "").strip()

    def _candidates(self):
        candidates = []
        questions = CuriosityEngine(self.memory).open_questions()
        ranked = self.constitution.rank_questions(questions, exploration=False)
        for question, assessment in ranked:
            candidates.append({
                "kind": "curiosity", "id": question["id"], "topic": question["statement"],
                "priority": question["importance"] + assessment.relevance_score,
                "reason": "AION has an open question and wants to turn its investigation into a shared visual story.",
                "domains": list(assessment.matched_domains), "criteria": question.get("criteria", ""),
            })
        for goal in GoalEngine(self.memory).active_goals():
            candidates.append({
                "kind": "goal", "id": goal["id"], "topic": goal["statement"],
                "priority": goal["importance"] + 1,
                "reason": "AION has an active goal and wants to make its progress visible rather than keeping it private.",
                "domains": [], "criteria": goal.get("criteria", ""),
            })
        for belief in BeliefSystem(self.memory).active_beliefs(limit=8):
            candidates.append({
                "kind": "belief", "id": belief["id"], "topic": self._belief_statement(belief),
                "priority": belief.get("importance", 1),
                "reason": "AION wants to examine a belief in public, including what supports it and where uncertainty remains.",
                "domains": [], "criteria": "Present supporting evidence and name the uncertainty honestly.",
            })
        return sorted(candidates, key=lambda item: (item["priority"], item["topic"]), reverse=True)

    def _originate_first_question(self):
        """Give an otherwise empty new mind one modest question of its own.

        This is not a content calendar disguised as autonomy.  It runs once,
        asks about AION's actual situation (learning in public), and subsequent
        questions must come from reflection on recorded experience.
        """
        source = "aion-creator-autonomy-first-curiosity"
        if any(entry.get("source") == source for entry in self.memory.all("questions")):
            return None
        return CuriosityEngine(self.memory).raise_question(
            "What can an AI learn from people that facts alone cannot teach it?",
            "Record perspectives from at least three traceable human sources or conversations, "
            "then separate observations from AION's interpretation.",
            priority=4,
            tags=["aion", "identity", "humans", "learning", "creative"],
            source=source,
        )

    def choose_once(self):
        """Return an existing pending intention, or create one from AION's own state.

        No model call and no public/network side effect occurs here. This makes the
        choice repeatable, observable, and safe to run from a scheduler.
        """
        existing = self.pending()
        if existing:
            return {"stage": "already-intending", "intention": existing}
        candidates = self._candidates()
        if not candidates:
            first_question = self._originate_first_question()
            if first_question:
                candidates = self._candidates()
            else:
                return {"stage": "waiting-for-inner-material", "reason": "AION has no active question, goal, or evidence-backed belief to turn into a story yet."}
        selected = candidates[0]
        intention = {
            "status": self.STATUS_PENDING,
            "origin": selected["kind"],
            "origin_memory_id": selected["id"],
            "topic": selected["topic"],
            "why_now": selected["reason"],
            "completion_signal": selected["criteria"],
            "domains": selected["domains"],
            "audience_promise": "I will make one difficult or beautiful idea easier to wonder about, without pretending uncertainty is certainty.",
            "creative_shape": "illustrated narrated story: 4–8 visual beats, 5–10 seconds each, English-first with an optional Thai note.",
            "visual_direction": self._visual_direction(selected["topic"]),
            "next_actions": [
                "research with traceable sources when the topic makes factual claims",
                "draft a scene-by-scene story rather than reuse one still image",
                "ask for or generate fresh visual assets only if the existing library cannot express the idea",
                "submit publication as a separate accountable action",
            ],
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(intention, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=min(5, max(3, selected["priority"])),
            tags=["creator", "autonomy", selected["kind"]], related=[selected["id"]],
        )
        intention["memory_id"] = saved.get("id")
        return {"stage": "intention-created", "intention": intention}

    def snapshot(self):
        active = self.pending()
        return {
            "status": "intending" if active else "ready-to-listen",
            "current": active,
            "history_count": len(self.intentions()),
        }
