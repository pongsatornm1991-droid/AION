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
from brain.creator_growth import CreatorGrowthGate
from brain.aion_director import AionDirector
from brain.watchability_gate import WatchabilityGate
from brain.story_genome import StoryGenome
from brain.creator_source_integrity import CreatorSourceIntegrity
from brain.aion_visual_director import AionVisualDirector


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

    @classmethod
    def _evidence_parts(cls, value, part_count=2, words_per_part=12):
        """Split a source observation without cutting a sentence mid-word.

        These are source-backed narration beats, not filler used to stretch a
        Reel.  If research supplies a short observation, a later timing gate
        returns it to Research/Story instead of padding a silent ending.
        """
        words = cls._clean(value, 520).split()
        parts = []
        for index in range(part_count):
            start = index * words_per_part
            fragment = " ".join(words[start:start + words_per_part]).strip()
            if fragment:
                parts.append(fragment.rstrip(" ,;:") + ".")
        return parts

    @staticmethod
    def _narrated_evidence(part, topic):
        """Keep a short source observation intelligible for a five-second beat."""
        if len(str(part).split()) >= 9:
            return part
        return f"{part} This is a direct observation about {topic}."

    @staticmethod
    def _episode_id(root_id, episode_format="short"):
        safe = re.sub(r"[^a-z0-9]+", "-", str(root_id).lower()).strip("-")
        digest = hashlib.sha256(str(root_id).encode("utf-8")).hexdigest()[:8]
        suffix = "long" if episode_format == "long-form" else "short"
        return f"aion-auto-{safe[:27] or 'research'}-{digest}-{suffix}"

    def _next_handoff(self, episode_format="short"):
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if not payload or payload.get("status") not in {"story-ready", "staged-for-studio"}:
                continue
            # A handoff can predate the source-integrity gate.  Keep that
            # audit record available, but never let it repeatedly break the
            # autonomous scheduler or enter a second production format.
            if not CreatorSourceIntegrity.assess(
                payload.get("sources"), payload.get("topic"), payload.get("completion_criteria")
            )["eligible"]:
                continue
            root_id = str(payload.get("root_question_id") or payload.get("memory_id") or "research")
            episode_id = self._episode_id(root_id, episode_format)
            if not (self.directory / f"{episode_id}.json").exists():
                return entry, payload
        return None, None

    def _episode(self, handoff, episode_format="short"):
        root_id = str(handoff.get("root_question_id") or handoff.get("memory_id") or "research")
        episode_id = self._episode_id(root_id, episode_format)
        topic = self._clean(handoff.get("topic"), 120) or "A question worth examining"
        sources = [item for item in (handoff.get("sources") or []) if item.get("url")][:2]
        if len(sources) < 2:
            raise ValueError("A Story Agent handoff needs two traceable sources before staging.")
        integrity = CreatorSourceIntegrity.assess(
            sources, handoff.get("topic"), handoff.get("completion_criteria")
        )
        if not integrity["eligible"]:
            raise ValueError(f"A Story Agent handoff needs suitable independent factual sources: {integrity['reason']}.")
        first, second = sources
        evidence_one = self._clean(first.get("observation"), 520)
        evidence_two = self._clean(second.get("observation"), 520)
        if not evidence_one or not evidence_two:
            raise ValueError("A Story Agent handoff needs a usable observation from each source.")
        first_parts = self._evidence_parts(evidence_one)
        second_parts = self._evidence_parts(evidence_two)
        first_title = self._clean(first.get("title"), 100) or "the first source"
        second_title = self._clean(second.get("title"), 100) or "the second source"
        uncertainty = self._clean(handoff.get("unknown_facts"), 260)
        title = self._clean(handoff.get("working_title"), 100) or f"AION Wonders: {topic}"
        audience_promise = self._clean(handoff.get("audience_value"), 240) or f"A viewer of any age can follow a clear, evidence-backed answer to: {topic}"
        visual_direction = AionVisualDirector.direct(
            topic,
            "illustrated-narrated-short" if episode_format == "short" else "long-form-illustrated",
        )
        episode = {
            "id": episode_id,
            "series": "AION Wonders",
            "title": title,
            "status": "storyboard-ready-needs-assets",
            "format": "illustrated-narrated-short",
            "target_duration_seconds": 60,
            "scene_seconds": 5,
            "pacing_policy": VisualStoryPolicy.VERSION,
            "audience_promise": audience_promise,
            "wonder_hook": topic,
            "growth_plan": CreatorGrowthGate.default_plan(topic, audience_promise),
            "topic_key": topic,
            "creative_device": "mystery-reveal",
            "age_layers": {
                "children": "Notice one surprising question and the clues that help answer it.",
                "family": "Compare what two sources say before deciding what to believe.",
                "deeper": "Separate direct observations from the interpretation built from them.",
            },
            "sources": [{"title": self._clean(source.get("title"), 160) or "Research source", "url": source["url"]} for source in sources],
            "uncertainty_boundary": uncertainty
                or "The available sources do not settle every part of this question.",
            "visual_direction": {
                "focus": "subject-first",
                "aion_role": "contextual-guide",
                "aion_frame_share_max": 0.20,
                "aion_presence_rationale": "AION is a small guide who helps viewers notice evidence; the subject and environment remain central.",
            },
            "visual_style": {
                "id": AionVisualDirector.VERSION,
                "summary": visual_direction["principle"],
                "director": visual_direction,
            },
            "visual_identity": {
                "version": VisualStoryPolicy.IDENTITY_VERSION,
                "character": VisualStoryPolicy.IDENTITY_SUMMARY,
                "environment": visual_direction["rendering_rule"],
                "prohibited": ["all-blue body", "all-blue outfit", "cape", "armour", "fashion pose", "embedded text", "logo", "watermark"],
            },
            "scenes": [
                {"n": 1, "beat": "hook", "visual": f"A cinematic educational opening centred on {topic}; the real subject and environment fill the frame, with AION only as a small guide at the edge.", "narration": f"Today we are asking: {topic}"},
                {"n": 2, "beat": "question", "visual": f"Show the central subject of {topic} clearly before any explanation; AION observes from the distant edge.", "narration": "We will follow what was actually observed, step by step, rather than inventing an answer."},
                {"n": 3, "beat": "evidence-one-intro", "visual": f"Show the first evidence scene for {topic}, guided by {first_title}; AION remains small and practical in the background.", "narration": f"Our first clue comes from {first_title}. We will use it to examine the subject closely."},
                {"n": 4, "beat": "evidence-one-a", "visual": f"Depict this documented observation about {topic}: {first_parts[0]} Keep the subject dominant; AION is a small guide only.", "narration": self._narrated_evidence(first_parts[0], topic)},
                {"n": 5, "beat": "evidence-one-b", "visual": f"Continue the first documented observation for {topic}: {(first_parts[1] if len(first_parts) > 1 else evidence_one)} Keep the evidence visible and AION in the background.", "narration": self._narrated_evidence(first_parts[1], topic) if len(first_parts) > 1 else f"This is the first direct observation connected to {topic}."},
                {"n": 6, "beat": "evidence-two-intro", "visual": f"Move to a distinct second evidence scene for {topic}, guided by {second_title}; AION remains small at the edge.", "narration": f"A second clue comes from {second_title}. We compare it carefully with the first observation."},
                {"n": 7, "beat": "evidence-two-a", "visual": f"Depict this documented observation about {topic}: {second_parts[0]} Keep the subject, action, and setting central; AION observes subtly from the distant edge.", "narration": self._narrated_evidence(second_parts[0], topic)},
                {"n": 8, "beat": "evidence-two-b", "visual": f"Continue the second documented observation for {topic}: {(second_parts[1] if len(second_parts) > 1 else evidence_two)} AION is only a small contextual guide.", "narration": self._narrated_evidence(second_parts[1], topic) if len(second_parts) > 1 else f"This gives us a second direct observation about {topic}."},
                {"n": 9, "beat": "connection", "visual": f"A visual comparison of the two documented observations about {topic}; show the subject and environment, with AION pointing only subtly from the edge.", "narration": f"Together, these two observations give us a clearer picture of {topic}."},
                {"n": 10, "beat": "boundary", "visual": f"Show the boundary between what the sources document and what they do not establish about {topic}; no invented action, AION remains in the background.", "narration": uncertainty or "The sources do not settle every detail, so we should not claim more than they show."},
                {"n": 11, "beat": "takeaway", "visual": f"Return to the central subject of {topic} in a final meaningful wide scene; AION is a small observer, not the focus.", "narration": f"The careful takeaway is simple: begin with what was observed about {topic}, then separate it from interpretation."},
                {"n": 12, "beat": "invitation", "visual": f"End on the real subject and environment of {topic}, leaving space for wonder; AION exits subtly at the edge.", "narration": "Keep asking better questions, and check the evidence with me."},
            ],
            "research_handoff_id": root_id,
            "story_package_id": handoff.get("story_package_id") or root_id,
            "content_angle_key": handoff.get("content_angle_key") or "evidence-walkthrough-short",
        }

        if episode_format == "long-form":
            # A primary episode is a distinct deliverable, not a stretched
            # Short.  It uses the same cited evidence but gives each source
            # observation room for setup, comparison and a clear uncertainty
            # boundary.  Every beat remains traceable to the handoff; no new
            # facts are invented merely to fill time.
            source_beats = []
            for source, label in ((first, first_title), (second, second_title)):
                parts = self._evidence_parts(source.get("observation"), part_count=6, words_per_part=8)
                for index, part in enumerate(parts, start=1):
                    source_beats.append({
                        "beat": f"evidence-{len(source_beats) + 1}",
                        "visual": f"Examine documented evidence from {label} about {topic}: {part} The subject and setting lead the frame; AION is a small guide only.",
                        "narration": self._narrated_evidence(part, topic),
                    })
            framing = [
                ("hook", f"Open on the most surprising visual question about {topic}; the subject fills the frame and AION is a small guide.", f"How can we explain {topic} without skipping what the evidence actually says?"),
                ("map-the-question", f"Orient the viewer in the real setting relevant to {topic}; show scale, place and context before the explanation.", f"We will take this one clue at a time and compare independent sources about {topic}."),
                ("first-source", f"Introduce {first_title} as the first evidence source for {topic}, showing what this source can and cannot directly support.", f"Our first source is {first_title}. It gives us a specific observation to examine."),
            ]
            bridge = [
                ("compare", f"Compare the two documented evidence trails about {topic} in one clear visual layout; do not turn interpretation into fact.", "Now compare the two sources. Agreement can strengthen a clue, but it does not answer every question by itself."),
                ("uncertainty", f"Show the limit of the available evidence around {topic}; retain the real setting and avoid invented details.", uncertainty or "The sources do not settle every detail, so we should not claim more than they show."),
                ("takeaway", f"Return to the subject of {topic} in a meaningful final wide scene, with AION only at the edge.", f"The useful takeaway is to start with what was observed about {topic}, then separate evidence from interpretation."),
                ("invitation", f"End on the real subject and environment of {topic}, leaving visual space for the viewer's next question.", "There is always more to learn when we follow the evidence carefully."),
            ]
            long_scenes = [
                {"n": index, "beat": beat, "visual": visual, "narration": narration}
                for index, (beat, visual, narration) in enumerate(framing + [(item["beat"], item["visual"], item["narration"]) for item in source_beats] + bridge, start=1)
            ]
            # A minimum two-minute primary episode needs 24 meaningful
            # five-second beats.  If evidence is concise, repeat the evidence
            # only as a different *inspection* (setting, mechanism, compare),
            # never as a silent filler shot.
            while len(long_scenes) < 24:
                source = source_beats[(len(long_scenes) - len(framing)) % len(source_beats)]
                number = len(long_scenes) + 1
                long_scenes.insert(-1, {
                    "n": number,
                    "beat": f"inspection-{number}",
                    "visual": f"Use a new environmental angle to inspect the evidence about {topic}: {source['narration']} Keep the subject central and AION subtle.",
                    "narration": f"Look again at this clue in context: {source['narration']}",
                })
            for number, scene in enumerate(long_scenes, start=1):
                scene["n"] = number
                if "aion" not in str(scene.get("visual") or "").lower():
                    scene["visual"] = (
                        f"{scene['visual']} AION appears briefly at the edge as a contextual guide."
                    )
            episode.update({
                "title": f"AION Explains: {topic}",
                "format": "long-form-illustrated",
                "target_duration_seconds": len(long_scenes) * 5,
                "scene_seconds": 5,
                "scenes": long_scenes,
                "content_angle_key": "evidence-walkthrough-primary",
            })
        episode["director_plan"] = AionDirector.plan(episode)
        episode["watchability_gate"] = WatchabilityGate.assess_storyboard(episode)
        episode["story_genome"] = StoryGenome(self.memory, self.root).snapshot()
        if not episode["watchability_gate"]["eligible"]:
            raise ValueError("Storyboard did not pass the AION Watchability Gate.")
        return episode

    def stage_once(self, episode_format="short"):
        if episode_format not in {"short", "long-form"}:
            raise ValueError("episode_format must be 'short' or 'long-form'")
        entry, handoff = self._next_handoff(episode_format)
        if entry is None:
            return {"stage": "no-story-ready-handoff"}
        episode = self._episode(handoff, episode_format)
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / f"{episode['id']}.json"
        if destination.exists():
            handoff["status"] = "staged-for-studio"
            handoff["episode_id"] = episode["id"]
            handoff["staged_formats"] = sorted(set(handoff.get("staged_formats") or []) | {episode_format})
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(handoff, ensure_ascii=False, sort_keys=True))
            return {"stage": "already-staged", "episode_id": episode["id"], "file": str(destination.relative_to(self.root)).replace("\\", "/")}
        destination.write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
        handoff["status"] = "staged-for-studio"
        handoff["episode_id"] = episode["id"]
        handoff["staged_formats"] = sorted(set(handoff.get("staged_formats") or []) | {episode_format})
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(handoff, ensure_ascii=False, sort_keys=True))
        return {"stage": "storyboard-staged", "episode_id": episode["id"], "file": str(destination.relative_to(self.root)).replace("\\", "/"), "scene_count": len(episode["scenes"])}
