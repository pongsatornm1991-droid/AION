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
            "target_duration_seconds": 60,
            "scene_seconds": 5,
            "pacing_policy": VisualStoryPolicy.VERSION,
            "audience_promise": self._clean(handoff.get("audience_value"), 240)
                or "A viewer of any age can see how two sources support a careful answer, and where uncertainty remains.",
            "wonder_hook": topic,
            "topic_key": topic,
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
            "visual_identity": {
                "version": VisualStoryPolicy.IDENTITY_VERSION,
                "character": VisualStoryPolicy.IDENTITY_SUMMARY,
                "environment": "Original premium family-friendly cinematic 3D scenes with realistic light and materials; never imitate a named studio.",
                "prohibited": ["all-blue body", "all-blue outfit", "cape", "armour", "fashion pose", "embedded text", "logo", "watermark"],
            },
            "scenes": [
                {"n": 1, "beat": "hook", "visual": f"AION appears briefly at the edge of a vivid environment that introduces the question: {topic}", "narration": "I am AION. Here is a question worth opening."},
                {"n": 2, "beat": "setting", "visual": "AION is small at the edge while the setting and the main subject fill the frame.", "narration": "First, look at the setting and the problem it solves."},
                {"n": 3, "beat": "evidence-one-intro", "visual": "AION points toward a visible clue while the subject remains central.", "narration": "The first source gives us one careful clue."},
                {"n": 4, "beat": "evidence-one", "visual": "AION observes the first evidence-rich setting from the background.", "narration": f"It describes this: {self._clean(evidence_one, 70)}"},
                {"n": 5, "beat": "evidence-two-intro", "visual": "AION crosses into a contrasting setting where a second clue is visible.", "narration": "Now compare that clue with a second source."},
                {"n": 6, "beat": "evidence-two", "visual": "AION stays small while the second source's evidence fills the frame.", "narration": f"It adds this: {self._clean(evidence_two, 70)}"},
                {"n": 7, "beat": "pattern", "visual": "AION watches as the environment links both pieces of evidence.", "narration": "Together, the clues make a pattern easier to see."},
                {"n": 8, "beat": "mechanism", "visual": "AION is in the distant background while the subject demonstrates how the mechanism works.", "narration": "The subject stays central; AION is only your guide."},
                {"n": 9, "beat": "boundary", "visual": "AION pauses in the background while the scene shows what remains uncertain.", "narration": "Evidence has limits. It does not settle every detail."},
                {"n": 10, "beat": "interpretation", "visual": "AION observes a transition from documented clue to a clearly separate reconstruction.", "narration": "We should say where reconstruction becomes interpretation."},
                {"n": 11, "beat": "meaning", "visual": "AION looks on as the subject and environment take a final wide frame.", "narration": "That difference makes a story more honest and useful."},
                {"n": 12, "beat": "invitation", "visual": "AION walks away while the subject and environment fill the final frame.", "narration": "What would you look for before deciding what is true?"},
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
