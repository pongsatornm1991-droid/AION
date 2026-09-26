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
from brain.visual_narrative_gate import VisualNarrativeGate
from brain.fact_first_visual_gate import FactFirstVisualGate
from brain.creator_source_integrity import CreatorSourceIntegrity
from brain.aion_visual_director import AionVisualDirector
from brain.aion_creative_director import AionCreativeDirector
from brain.evaluator import OutputEvaluator
from brain.story_beats import (
    BOUNDARY, COMPARE, CONNECTION, EVIDENCE_ONE_A, EVIDENCE_ONE_B, EVIDENCE_ONE_INTRO,
    EVIDENCE_TWO_A, EVIDENCE_TWO_B, EVIDENCE_TWO_INTRO, FIRST_SOURCE, HOOK, INVITATION,
    MAP_THE_QUESTION, QUESTION, TAKEAWAY, UNCERTAINTY, is_evidence_literal_beat,
)


class StoryEpisodeStager:
    """Convert one qualified research handoff into a subject-first Short."""

    CATEGORY = "creator_research_handoffs"
    SOURCE = "aion-story-episode-stager"

    # A source observation copy-pasted from an encyclopedia/paper abstract
    # often carries its original list-bullet markup ("- The article
    # describes... - It notes that..."). That "-" is Markdown structure,
    # not spoken content, and reading it aloud is exactly what made
    # narration sound like a research memo instead of a told story (owner
    # feedback, 2026-09-27). Matches a literal "- " at the very start of the
    # text or right after a sentence boundary, never a real hyphen inside or
    # between words (e.g. "real-time"), which never has surrounding spaces.
    _BULLET_ARTIFACT = re.compile(r"(^|(?<=[.!?]) )-\s+")

    def __init__(self, memory, root, provider=None):
        self.memory = memory
        self.root = Path(root)
        self.directory = self.root / "content" / "creator_series"
        self.provider = provider

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @classmethod
    def _clean(cls, value, limit=220):
        """Collapse whitespace, drop bullet markup, but never cut mid-word.

        Found 2026-09-22: a bare `[:limit]` character slice could cut the
        last word in half (an octopus episode's narration read "...deep
        reddish pu" -- the source text ran past 520 characters right in
        the middle of "purple"). _evidence_parts()'s own docstring already
        promised "without cutting a sentence mid-word"; this is what
        actually keeps that promise.
        """
        text = " ".join(str(value or "").split())
        text = cls._BULLET_ARTIFACT.sub(lambda match: match.group(1), text)
        if len(text) <= limit:
            return text.strip()
        truncated = text[:limit]
        boundary = truncated.rfind(" ")
        if boundary > 0:
            truncated = truncated[:boundary]
        return truncated.strip()

    @classmethod
    def _evidence_parts(cls, value, part_count=2, words_per_part=12):
        """Split a source observation into spoken-length narration beats.

        These are source-backed narration beats, not filler used to stretch a
        Reel -- every word still comes from the source, nothing is invented.
        Each beat's boundary prefers a real sentence ending within a natural
        window around `words_per_part` (found 2026-09-27: a blind word-count
        cut landed mid-clause on almost every multi-sentence observation,
        e.g. "...satellite imagery." stopping right after a list separator
        instead of at the sentence's own end). A comma is the next best
        boundary -- still a real pause in the source's own text, just not a
        full sentence end. Only a source sentence longer than the whole
        window forces a blind word-count cut; that fragment ends in an
        ellipsis rather than a fabricated period, so it honestly reads as a
        continuing thought instead of a false complete sentence. If research
        supplies a short observation, a later timing gate returns it to
        Research/Story instead of padding a silent ending.

        This function's own word-count window (up to 1.6x words_per_part)
        is deliberately not a hard cap against the beat's fixed
        `scene_seconds`: brain/narration_preflight.py's NarrationPreflight
        already measures each beat's *real* synthesized voice duration
        (not a word-count guess) before any scene image is generated, and
        automatically splits any beat that actually runs long, remeasuring
        afterward. That real-audio gate is strictly more accurate than a
        word-count heuristic added here could ever be, so none is added.
        """
        words = cls._clean(value, 520).split()
        parts = []
        start = 0
        for _ in range(part_count):
            if start >= len(words):
                break
            min_end = start + max(1, round(words_per_part * 0.6))
            max_end = min(start + round(words_per_part * 1.6), len(words))
            end = None
            for candidate in range(max_end, start, -1):
                if candidate >= min_end and words[candidate - 1].rstrip(",;:\"')").endswith((".", "!", "?")):
                    end = candidate
                    break
            natural_sentence_end = end is not None
            if end is None:
                for candidate in range(max_end, start, -1):
                    if candidate >= min_end and words[candidate - 1].endswith(","):
                        end = candidate
                        break
            if end is None:
                end = min(start + words_per_part, len(words))
            fragment = " ".join(words[start:end]).strip()
            if fragment:
                # A short observation can run out of words before `min_end`
                # is ever reached, so neither boundary search above ever
                # fires even though the blind cut happens to land exactly
                # on the text's own real ending -- checking the fragment's
                # own last word here (not just whether the windowed search
                # "found" it) stops a short, already-complete source
                # sentence like "Ice was stored below ground." from getting
                # a spurious "…" tacked on after its own period.
                if natural_sentence_end or fragment.endswith((".", "!", "?")):
                    pass
                elif fragment.endswith(","):
                    fragment = fragment.rstrip(",") + "."
                else:
                    fragment = fragment.rstrip(" ,;:") + "…"
                parts.append(fragment)
            start = end
        return parts

    @staticmethod
    def _narrated_evidence(part, topic):
        """Keep a short source observation intelligible for a five-second beat."""
        if len(str(part).split()) >= 9:
            return part
        return f"{part} This is a direct observation about {topic}."

    @staticmethod
    def _rewritable_beat(beat):
        """Beats whose narration is a literal (or near-literal) excerpt of a
        source observation -- the ones an AI rewrite is meant to retell, not
        the already hand-authored template lines (question, boundary,
        takeaway, invitation, ...), which stay as they are. Delegates to
        brain.story_beats so this can never drift from the exact strings
        this same class writes into a scene's own "beat" field below."""
        return is_evidence_literal_beat(beat)

    @staticmethod
    def _key_terms(text):
        """Rough proper-noun/number fingerprint of a piece of source text.

        Not a real NER model -- a plain, honest heuristic (capitalized or
        digit-bearing tokens) used only to catch an AI rewrite that drifted
        away from the facts it was given, not to prove correctness.
        """
        return {
            token.strip(".,;:!?\"'()")
            for token in str(text or "").split()
            if token.strip(".,;:!?\"'()") and (token[0].isupper() or any(char.isdigit() for char in token))
        }

    @classmethod
    def _preserves_key_facts(cls, original, rewritten):
        key_terms = cls._key_terms(original)
        if not key_terms:
            return True
        rewritten_lower = str(rewritten or "").lower()
        kept = sum(1 for term in key_terms if term.lower() in rewritten_lower)
        return (kept / len(key_terms)) >= 0.6

    def _rewrite_scene_narrations(self, scenes, topic):
        """Retell each evidence-literal beat as natural, engaging spoken
        narration, using only facts already present in that beat's own
        current narration -- never inventing a new fact, number, name, or
        claim, and never letting AION claim to feel or be conscious.

        Owner feedback, 2026-09-27: "ทำให้เป็นคอนเทนที่สนุก ฟังแล้วไม่ใช่
        เหมือนนั่งเรียน... ให้ AI เขียนบทใหม่จากหลักฐานเดิม" (make it fun
        content, not like sitting in class; have AI write a fresh script
        from the same evidence). This is a deliberate, requested trade
        against the module's long-standing default of narrating a literal
        source excerpt -- every rewrite is still screened against
        claim-safety and a rough fact-preservation check before use, and
        any beat that fails either check, or the whole pass if no provider
        is configured (offline/test paths, or a real provider outage),
        quietly keeps its original literal narration instead of blocking
        staging. Returns (scenes, meta) -- meta is recorded on the episode
        for the same auditability reason visual_style/aion_deliberation
        record their own "bounded-fallback" origin.
        """
        targets = [scene for scene in scenes if self._rewritable_beat(scene.get("beat"))]
        if self.provider is None:
            return scenes, {"version": "ai-narration-rewrite-v1", "origin": "bounded-fallback", "reason": "provider-unavailable"}
        if not targets:
            return scenes, {"version": "ai-narration-rewrite-v1", "origin": "bounded-fallback", "reason": "no-rewritable-beats"}

        prompt = "\n".join([
            "You are helping AION, an AI documentary narrator, retell short evidence-grounded beats as fun, natural, engaging spoken narration for a fast-paced short video.",
            "Absolute rules:",
            "- Use ONLY information already present in each beat's own given text. Never add a new fact, number, name, or claim that is not already stated there.",
            "- Never phrase anything as AION having feelings, consciousness, or subjective experience -- AION is an AI narrator describing evidence, never a sentient being.",
            "- Keep each beat's rewrite close to its target word count (+/-25%), since it must still fit a fixed five-second scene.",
            "- Sound like a curious, energetic documentary narrator talking directly to a viewer -- never a research abstract, never a bullet list.",
            f"Topic of the whole video: {topic}",
            "Rewrite each beat below. Return ONLY a JSON object mapping each beat's scene number (as a string) to its rewritten narration string -- no markdown fences, no commentary, no extra keys.",
            json.dumps(
                {str(scene["n"]): {"original": scene["narration"], "target_words": len(str(scene["narration"]).split())} for scene in targets},
                ensure_ascii=False,
            ),
        ])
        try:
            raw = self.provider.generate(prompt).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:]
            rewritten_by_number = json.loads(raw.strip())
            if not isinstance(rewritten_by_number, dict):
                raise ValueError("expected a JSON object mapping scene numbers to rewritten narration")
        except Exception as exc:
            return scenes, {"version": "ai-narration-rewrite-v1", "origin": "bounded-fallback", "reason": f"provider-error:{type(exc).__name__}"}

        applied, skipped = [], []
        for scene in targets:
            candidate = rewritten_by_number.get(str(scene["n"]))
            if not isinstance(candidate, str) or not candidate.strip():
                skipped.append({"n": scene["n"], "reason": "missing-or-empty"})
                continue
            if OutputEvaluator.has_unsafe_claim(candidate):
                skipped.append({"n": scene["n"], "reason": "claim-safety"})
                continue
            if not self._preserves_key_facts(scene["narration"], candidate):
                skipped.append({"n": scene["n"], "reason": "fact-drift"})
                continue
            scene["narration"] = candidate.strip()
            applied.append(scene["n"])

        if not applied:
            return scenes, {"version": "ai-narration-rewrite-v1", "origin": "bounded-fallback", "reason": "no-candidate-passed-checks", "skipped": skipped}
        return scenes, {
            "version": "ai-narration-rewrite-v1", "origin": "ai-rewrite",
            "rewritten_scenes": applied, "skipped": skipped,
        }

    @staticmethod
    def _episode_id(root_id, episode_format="short"):
        safe = re.sub(r"[^a-z0-9]+", "-", str(root_id).lower()).strip("-")
        digest = hashlib.sha256(str(root_id).encode("utf-8")).hexdigest()[:8]
        suffix = "long" if episode_format == "long-form" else "short"
        return f"aion-auto-{safe[:27] or 'research'}-{digest}-{suffix}"

    def _next_handoff(self, episode_format="short", exclude_ids=None):
        exclude_ids = exclude_ids or set()
        for entry in self.memory.all(self.CATEGORY):
            if entry.get("id") in exclude_ids:
                continue
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
        creative_deliberation = AionCreativeDirector.propose(
            topic, audience_promise,
            "illustrated-narrated-short" if episode_format == "short" else "long-form-illustrated",
            self.provider,
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
            "sources": [{
                "title": self._clean(source.get("title"), 160) or "Research source",
                "url": source["url"],
                "observation": self._clean(source.get("observation"), 520),
            } for source in sources],
            # Carries the source decision into paid-image preflight. It is
            # evidence about the storyboard's eligibility, not a claim for a
            # viewer, and prevents a later stage from forgetting why it was
            # safe to produce.
            "evidence_integrity": integrity,
            "uncertainty_boundary": uncertainty
                or "The available sources do not settle every part of this question.",
            "visual_direction": {
                "focus": "subject-first",
                "aion_role": "contextual-guide",
                "aion_frame_share_max": 0.20,
                "aion_presence_rationale": "AION is a small guide who helps viewers notice evidence; the subject and environment remain central.",
            },
            "visual_style": {
                # The director may choose the setting, wardrobe and story
                # device, but the channel's medium stays consistent across
                # ordinary releases. Auto-staged through the current policy
                # pipeline, so it is pre-approved for release; a manually
                # placed or experimental episode must be approved explicitly
                # before it can win a release slot (see YouTubeCreatorQueue).
                "id": VisualStoryPolicy.CHANNEL_VISUAL_STYLE,
                "approved": True,
                "summary": creative_deliberation["premise"],
                "director": visual_direction,
                "aion_deliberation": creative_deliberation,
            },
            "visual_identity": {
                "version": VisualStoryPolicy.IDENTITY_VERSION,
                "character": VisualStoryPolicy.IDENTITY_SUMMARY,
                "environment": visual_direction["rendering_rule"],
                "prohibited": ["all-blue body", "all-blue outfit", "cape", "armour", "fashion pose", "embedded text", "logo", "watermark"],
            },
            "scenes": [
                {"n": 1, "beat": HOOK, "visual": f"A cinematic educational opening centred on {topic}; the real subject and environment fill the frame, with AION only as a small guide at the edge.",
                 # Found 2026-09-22 (owner: focus on Shorts, aim for
                 # kurzgesagt-calibre memorability): "Today we are asking:
                 # {topic}" is throat-clearing -- it announces the show
                 # instead of hooking the viewer, and every episode opened
                 # on the identical weak preamble. Lead with the concrete,
                 # sourced fact instead, then land the question -- the
                 # fact itself still comes only from research's own
                 # sourced observation, nothing invented here.
                 "narration": f"{first_parts[0]} {topic}"},
                {"n": 2, "beat": QUESTION, "visual": f"Show the central subject of {topic} clearly before any explanation; AION observes from the distant edge.", "narration": "We will follow what was actually observed, step by step, rather than inventing an answer."},
                {"n": 3, "beat": EVIDENCE_ONE_INTRO, "visual": f"Show the first evidence scene for {topic}, guided by {first_title}; AION remains small and practical in the background.", "narration": f"Our first clue comes from {first_title}. We will use it to examine the subject closely."},
                {"n": 4, "beat": EVIDENCE_ONE_A, "visual": f"Depict this documented observation about {topic}: {first_parts[0]} Keep the subject dominant; AION is a small guide only.", "narration": self._narrated_evidence(first_parts[0], topic)},
                {"n": 5, "beat": EVIDENCE_ONE_B, "visual": f"Continue the first documented observation for {topic}: {(first_parts[1] if len(first_parts) > 1 else evidence_one)} Keep the evidence visible and AION in the background.", "narration": self._narrated_evidence(first_parts[1], topic) if len(first_parts) > 1 else f"This is the first direct observation connected to {topic}."},
                {"n": 6, "beat": EVIDENCE_TWO_INTRO, "visual": f"Move to a distinct second evidence scene for {topic}, guided by {second_title}; AION remains small at the edge.", "narration": f"A second clue comes from {second_title}. We compare it carefully with the first observation."},
                {"n": 7, "beat": EVIDENCE_TWO_A, "visual": f"Depict this documented observation about {topic}: {second_parts[0]} Keep the subject, action, and setting central; AION observes subtly from the distant edge.", "narration": self._narrated_evidence(second_parts[0], topic)},
                {"n": 8, "beat": EVIDENCE_TWO_B, "visual": f"Continue the second documented observation for {topic}: {(second_parts[1] if len(second_parts) > 1 else evidence_two)} AION is only a small contextual guide.", "narration": self._narrated_evidence(second_parts[1], topic) if len(second_parts) > 1 else f"This gives us a second direct observation about {topic}."},
                {"n": 9, "beat": CONNECTION, "visual": f"A visual comparison of the two documented observations about {topic}; show the subject and environment, with AION pointing only subtly from the edge.",
                 # Found 2026-09-22 (quality_incident: "generic-template-
                 # story-does-not-explain-topic"): this beat used to say
                 # only "these two observations give us a clearer picture,"
                 # a content-free line the episode never actually earned.
                 # Restate what the two sources actually said, together, so
                 # the story has a real synthesis moment instead of a filler
                 # transition -- the mechanism itself still comes from
                 # research's own sourced observations, never invented here.
                 "narration": f"Put together: {first_parts[0]} And from the second source: {second_parts[0] if second_parts else evidence_two}"},
                {"n": 10, "beat": BOUNDARY, "visual": f"Show the boundary between what the sources document and what they do not establish about {topic}; no invented action, AION remains in the background.", "narration": uncertainty or "The sources do not settle every detail, so we should not claim more than they show."},
                {"n": 11, "beat": TAKEAWAY, "visual": f"Return to the central subject of {topic} in a final meaningful wide scene; AION is a small observer, not the focus.", "narration": f"The careful takeaway is simple: begin with what was observed about {topic}, then separate it from interpretation."},
                {"n": 12, "beat": INVITATION, "visual": f"End on the real subject and environment of {topic}, leaving space for wonder; AION exits subtly at the edge.",
                 # Found 2026-09-22: "Keep asking better questions, and
                 # check the evidence with me" is the exact same closing
                 # line on every single episode regardless of topic -- it
                 # leaves nothing topic-specific for a viewer to carry
                 # away or rewatch for. Close on the actual subject instead,
                 # so the takeaway is something concrete, not a generic
                 # sign-off. Must not end on "?" (WatchabilityGate) --
                 # topic itself is a question, so this closes past it, not
                 # on it.
                 "narration": f"That's the real story behind {topic} Notice it again, and you will see it differently next time."},
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
                (HOOK, f"Open on the most surprising visual question about {topic}; the subject fills the frame and AION is a small guide.", f"How can we explain {topic} without skipping what the evidence actually says?"),
                (MAP_THE_QUESTION, f"Orient the viewer in the real setting relevant to {topic}; show scale, place and context before the explanation.", f"We will take this one clue at a time and compare independent sources about {topic}."),
                (FIRST_SOURCE, f"Introduce {first_title} as the first evidence source for {topic}, showing what this source can and cannot directly support.", f"Our first source is {first_title}. It gives us a specific observation to examine."),
            ]
            bridge = [
                (COMPARE, f"Compare the two documented evidence trails about {topic} in one clear visual layout; do not turn interpretation into fact.", "Now compare the two sources. Agreement can strengthen a clue, but it does not answer every question by itself."),
                (UNCERTAINTY, f"Show the limit of the available evidence around {topic}; retain the real setting and avoid invented details.", uncertainty or "The sources do not settle every detail, so we should not claim more than they show."),
                (TAKEAWAY, f"Return to the subject of {topic} in a meaningful final wide scene, with AION only at the edge.", f"The useful takeaway is to start with what was observed about {topic}, then separate evidence from interpretation."),
                (INVITATION, f"End on the real subject and environment of {topic}, leaving visual space for the viewer's next question.", "There is always more to learn when we follow the evidence carefully."),
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
        episode["scenes"], episode["narration_style"] = self._rewrite_scene_narrations(episode["scenes"], topic)
        episode["visual_narrative"] = VisualNarrativeGate.plan(topic, episode["scenes"])
        episode["fact_first_visual"] = FactFirstVisualGate.plan(topic, handoff.get("sources"), episode["scenes"])
        visual_narrative = VisualNarrativeGate.assess(episode)
        if not visual_narrative["eligible"]:
            raise ValueError("Storyboard did not pass the AION Visual Narrative Gate.")
        fact_visual = FactFirstVisualGate.assess(episode)
        if not fact_visual["eligible"]:
            raise ValueError("Storyboard did not pass the AION Fact-First Visual Gate.")
        episode["director_plan"] = AionDirector.plan(episode)
        episode["watchability_gate"] = WatchabilityGate.assess_storyboard(episode)
        episode["story_genome"] = StoryGenome(self.memory, self.root).snapshot()
        if not episode["watchability_gate"]["eligible"]:
            raise ValueError("Storyboard did not pass the AION Watchability Gate.")
        return episode

    def _stage_entry(self, entry, handoff, episode_format):
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

    def stage_once(self, episode_format="short"):
        if episode_format not in {"short", "long-form"}:
            raise ValueError("episode_format must be 'short' or 'long-form'")
        entry, handoff = self._next_handoff(episode_format)
        if entry is None:
            return {"stage": "no-story-ready-handoff"}
        return self._stage_entry(entry, handoff, episode_format)

    def stage_batch(self, limit=1, episode_format="short"):
        """Stage up to `limit` qualified research handoffs in one shift.

        research-to-story.yml used to call stage_once() exactly once per
        three-hour tick, so a backlog of already-qualified, evidence-grounded
        handoffs could sit unstaged for hours even though nothing was
        actually blocking them -- the cap was an arbitrary per-run limit,
        not a quality gate. This mirrors
        CreatorSceneProduction.produce_ready_episodes(): a bounded shift,
        not an unbounded content farm. A handoff that fails a downstream
        gate (Fact-First Visual / Watchability) is skipped for the rest of
        THIS call only -- its stored status is left untouched, so a later
        run can still reconsider it once the upstream research is fixed --
        and staging continues with the next qualified handoff instead of
        aborting the whole shift.
        """
        if episode_format not in {"short", "long-form"}:
            raise ValueError("episode_format must be 'short' or 'long-form'")
        results = []
        excluded = set()
        for _ in range(max(1, int(limit))):
            entry, handoff = self._next_handoff(episode_format, exclude_ids=excluded)
            if entry is None:
                break
            try:
                result = self._stage_entry(entry, handoff, episode_format)
            except ValueError as exc:
                excluded.add(entry.get("id"))
                results.append({"stage": "handoff-skipped", "reason": str(exc), "handoff_id": entry.get("id")})
                continue
            results.append(result)
        if not results:
            return {"stage": "no-story-ready-handoff", "results": []}
        staged = [r for r in results if r.get("stage") in {"storyboard-staged", "already-staged"}]
        return {
            "stage": "story-batch-complete" if staged else results[-1].get("stage"),
            "staged_episode_ids": [r.get("episode_id") for r in staged],
            "results": results,
        }
