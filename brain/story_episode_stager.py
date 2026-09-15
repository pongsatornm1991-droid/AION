"""Stage research-grounded Story Agent handoffs as Studio storyboards.

This is the bridge between private research memory and the public Creator
Studio production queue.  It writes a small, traceable storyboard only; it
does not generate media, spend money, or publish to any platform.
"""

import hashlib
import json
import re
from pathlib import Path

from brain.visual_story_policy import VisualStoryPolicy


class StoryEpisodeStager:
    """Convert one qualified research handoff into a subject-first Short."""

    CATEGORY = "creator_research_handoffs"
    SOURCE = "aion-story-episode-stager"

    def __init__(self, memory, root):
        self.memory = memory
        self.root = Path(root)
        self.directory = self.root / "content" / "creator_series"

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _clean(value, limit=220):
        return " ".join(str(value or "").split())[:limit].strip()

    @staticmethod
    def _episode_id(root_id):
        safe = re.sub(r"[^a-z0-9]+", "-", str(root_id).lower()).strip("-")
        digest = hashlib.sha256(str(root_id).encode("utf-8")).hexdigest()[:8]
        return f"aion-auto-{safe[:32] or 'research'}-{digest}"

    def _next_handoff(self):
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload and payload.get("status") == "story-ready":
                return entry, payload
        return None, None

    def _episode(self, handoff):
        root_id = str(handoff.get("root_question_id") or handoff.get("memory_id") or "research")
        episode_id = self._episode_id(root_id)
        topic = self._clean(handoff.get("topic"), 120) or "A question worth examining"
        sources = [item for item in (handoff.get("sources") or []) if item.get("url")][:2]
        if len(sources) < 2:
            raise ValueError("A Story Agent handoff needs two traceable sources before staging.")
        first, second = sources
        evidence_one = self._clean(first.get("observation"), 180) or "The first source gives one piece of the evidence."
        evidence_two = self._clean(second.get("observation"), 180) or "A second source lets us test the first interpretation."
        title = self._clean(handoff.get("working_title"), 100) or f"AION Wonders: {topic}"
        return {
            "id": episode_id,
            "series": "AION Wonders",
            "title": title,
            "status": "storyboard-ready-needs-assets",
            "format": "illustrated-narrated-short",
            "target_duration_seconds": 25,
            "scene_seconds": 5,
            "pacing_policy": VisualStoryPolicy.VERSION,
            "audience_promise": self._clean(handoff.get("audience_value"), 240)
                or "A viewer of any age can see how two sources support a careful answer, and where uncertainty remains.",
            "wonder_hook": topic,
            "creative_device": "mystery-reveal",
            "age_layers": {
                "children": "Notice one surprising question and the clues that help answer it.",
                "family": "Compare what two sources say before deciding what to believe.",
                "deeper": "Separate direct observations from the interpretation built from them.",
            },
            "sources": [{"title": self._clean(source.get("title"), 160) or "Research source", "url": source["url"]} for source in sources],
            "uncertainty_boundary": self._clean(handoff.get("unknown_facts"), 280)
                or "The available sources do not settle every part of this question.",
            "visual_direction": {
                "focus": "subject-first",
                "aion_role": "contextual-guide",
                "aion_frame_share_max": 0.20,
                "aion_presence_rationale": "AION is a small guide who helps viewers notice evidence; the subject and environment remain central.",
            },
            "scenes": [
                {"n": 1, "beat": "hook", "visual": f"AION appears briefly at the edge of a vivid environment that introduces the question: {topic}", "narration": f"I am AION. Here is a question worth looking at: {topic}"},
                {"n": 2, "beat": "evidence-one", "visual": "AION stands small beside the primary subject while the environment and evidence take the frame.", "narration": f"One source gives us this clue: {evidence_one}"},
                {"n": 3, "beat": "evidence-two", "visual": "AION observes a second evidence-rich setting while the subject remains dominant in the frame.", "narration": f"A second source helps us compare it: {evidence_two}"},
                {"n": 4, "beat": "boundary", "visual": "AION pauses in the background while a realistic scene shows the limits of what can be known.", "narration": "The evidence helps, but it does not answer every part of the mystery."},
                {"n": 5, "beat": "invitation", "visual": "AION walks away as the subject and environment fill the final wide frame.", "narration": "What would you look for next before deciding what is true?"},
            ],
            "research_handoff_id": root_id,
        }

    def stage_once(self):
        entry, handoff = self._next_handoff()
        if entry is None:
            return {"stage": "no-story-ready-handoff"}
        episode = self._episode(handoff)
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / f"{episode['id']}.json"
        if destination.exists():
            handoff["status"] = "staged-for-studio"
            handoff["episode_id"] = episode["id"]
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(handoff, ensure_ascii=False, sort_keys=True))
            return {"stage": "already-staged", "episode_id": episode["id"], "file": str(destination.relative_to(self.root)).replace("\\", "/")}
        destination.write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
        handoff["status"] = "staged-for-studio"
        handoff["episode_id"] = episode["id"]
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(handoff, ensure_ascii=False, sort_keys=True))
        return {"stage": "storyboard-staged", "episode_id": episode["id"], "file": str(destination.relative_to(self.root)).replace("\\", "/"), "scene_count": len(episode["scenes"])}
