"""Turn one grounded research package into traceable *candidate* angles.

An expansion map makes the reuse of research explicit without pretending that
one source pair proves every related claim.  The original brief is the only
production-ready angle.  Each follow-up question is preserved and must earn
its own independent evidence before the normal story pipeline may use it.
"""

import json

from .curiosity import CuriosityEngine


class ContentExpansionPlanner:
    """Plan, preserve and gradually research non-duplicative follow-up angles."""

    CATEGORY = "content_expansion_maps"
    SOURCE = "aion-content-expansion"
    MAX_SEED_PER_SHIFT = 2
    MAX_ANGLES_PER_STORY = 4

    # Every solid subject can become more than one useful Short, but the
    # follow-ups must not be a padded retelling of the parent.  These three
    # editorial lenses make each continuation do a different job for the
    # viewer: show the mechanism, connect it to an observation, or clarify a
    # boundary.  They are deliberately questions, never claims inherited
    # from the parent package.
    GENERIC_CREATOR_ANGLES = (
        (
            "mechanism",
            "What is the smallest observable mechanism that helps answer: {topic}",
            "Zoom in on one moving part, then reveal how that small change produces the larger effect.",
        ),
        (
            "everyday-test",
            "Where could someone notice or test the idea behind: {topic}",
            "Begin with a familiar scene, then connect it to one evidence-backed observation.",
        ),
        (
            "boundary",
            "What does this explanation not automatically mean: {topic}",
            "Show the tempting oversimplification beside the supported boundary, ending with a clearer question.",
        ),
    )

    # These are editorial questions, not factual answers.  They turn a broad,
    # already-grounded topic into narrower questions a researcher can verify.
    FAMILY_ANGLES = {
        "human-history-clothing": (
            ("What problems besides cold did early clothing help people solve?", "Show protection, movement, identity, and status as separate possibilities rather than one universal reason."),
            ("How did the materials people wore change with place and technology?", "Compare a few materials and environments without claiming one timeline for every society."),
        ),
        "human-history-money": (
            ("What problem does money solve that direct barter makes difficult?", "Show two people struggling to match needs, then a shared way to compare value."),
            ("Why did communities use different things as money?", "Show that usefulness, trust, and shared acceptance can matter more than a single material."),
        ),
        "moon-living": (
            ("How could a Moon habitat provide air and water?", "Follow one sealed habitat looping essential resources instead of treating the Moon like Earth."),
            ("Why is radiation a major challenge for living on the Moon?", "Contrast Earth's protective atmosphere and magnetic field with a lunar surface shelter."),
        ),
        "human-history-writing": (
            ("How did early writing help people keep track of trade and supplies?", "Follow a simple record from goods to marks, while keeping dates and places source-specific."),
            ("How did writing change who could send information far away?", "Contrast memory and speech with a durable message moving between places."),
        ),
        "human-history-law": (
            ("What problem can written laws solve in a growing community?", "Show a public rule reducing disagreement without claiming laws were equally fair to everyone."),
            ("Why do laws change over time?", "Show new situations testing an old rule; research one documented example before narration."),
        ),
        "human-history-farming": (
            ("What trade-offs came with settling near crops?", "Balance stored food and permanence against new work and risk; do not frame farming as automatically better."),
            ("How did seasonal observation help early farming?", "Use one place and one crop only after its evidence is independently sourced."),
        ),
    }

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def maps(self):
        result = []
        for entry in self.memory.all(self.CATEGORY):
            value = self._payload(entry)
            if value:
                result.append({**value, "memory_id": entry.get("id"), "timestamp": entry.get("timestamp")})
        return sorted(result, key=lambda item: item.get("timestamp", ""), reverse=True)

    @staticmethod
    def _family(brief):
        tags = {str(tag) for tag in brief.get("question_tags") or []}
        return next((tag for tag in tags if tag in ContentExpansionPlanner.FAMILY_ANGLES), None)

    @classmethod
    def _follow_up_angles(cls, brief, family):
        """Return a small, varied Creator mini-series for one source package.

        Family-specific angles keep subjects such as money or Moon living
        concrete.  The generic lenses then fill the remaining slots for any
        evidence-backed subject, so a science story is not artificially
        limited to one episode just because it lacks a hand-written family.
        """
        topic = str(brief.get("topic") or "this question").strip()
        angles = []
        for index, (question, visual) in enumerate(cls.FAMILY_ANGLES.get(family, ())):
            angles.append({
                "angle_key": f"{family or 'general'}-specific-{index + 1}",
                "angle_type": "specific-follow-up",
                "question": question,
                "visual_metaphor": visual,
                "status": "needs-independent-evidence",
            })

        for angle_type, question_template, visual in cls.GENERIC_CREATOR_ANGLES:
            question = question_template.format(topic=topic)
            if question.lower() in {item["question"].lower() for item in angles}:
                continue
            angles.append({
                "angle_key": f"{family or 'general'}-{angle_type}",
                "angle_type": angle_type,
                "question": question,
                "visual_metaphor": visual,
                "status": "needs-independent-evidence",
            })
            if len(angles) >= cls.MAX_ANGLES_PER_STORY:
                break
        return angles

    def create_for_brief(self, brief):
        """Persist an angle map once; it never stages or publishes anything."""
        root_id = str(brief.get("root_question_id") or "").strip()
        if not root_id:
            return {"stage": "expansion-skipped-missing-root", "map": None}
        existing = next((item for item in self.maps() if item.get("root_question_id") == root_id), None)
        if existing:
            return {"stage": "expansion-map-exists", "map": existing}
        family = self._family(brief)
        topic = str(brief.get("topic") or "this question").strip()
        angles = self._follow_up_angles(brief, family)
        source_urls = [str(item.get("url") or "") for item in brief.get("sources") or [] if item.get("url")]
        expansion_map = {
            "version": 2,
            "status": "planned",
            "root_question_id": root_id,
            "story_package_id": brief.get("story_package_id") or root_id,
            "topic": brief.get("topic"),
            "family": family,
            "parent_source_urls": source_urls,
            "primary": {
                "angle_key": brief.get("content_angle_key") or "evidence-walkthrough",
                "topic": brief.get("topic"),
                "status": "research-ready-primary",
            },
            "creator_series_summary": {
                "series_shape": "one surprising question, then distinct mechanism, everyday, and boundary episodes",
                "core_story": topic,
                "planned_episode_count": 1 + len(angles),
                "storytelling_rule": (
                    "Each Short must open with one concrete surprise, show one visual change, "
                    "deliver one evidence-backed reveal, and end with a useful takeaway or next question."
                ),
            },
            "follow_up_angles": angles,
            "boundary": (
                "Parent sources provide context only for follow-ups. Each follow-up must obtain "
                "its own independent traceable evidence, novelty approval, and full production "
                "Quality Gates before it can become a separate Short."
            ),
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(expansion_map, ensure_ascii=False, sort_keys=True),
            memory_type="decision", source=self.SOURCE, importance=4,
            tags=["creator", "content-expansion", family or "no-curated-family"],
            related=[root_id] + [item.get("evidence_memory_id") for item in brief.get("sources") or [] if item.get("evidence_memory_id")],
        )
        expansion_map["memory_id"] = saved.get("id")
        return {"stage": "expansion-map-created", "map": expansion_map}

    def seed_pending_questions(self, limit=None):
        """Open a bounded number of preserved follow-ups when the queue has room."""
        limit = self.MAX_SEED_PER_SHIFT if limit is None else max(0, int(limit))
        curiosity = CuriosityEngine(self.memory)
        existing = {str(item.get("statement") or "").strip().lower() for item in curiosity.open_questions()}
        created = []
        for expansion_map in reversed(self.maps()):
            for angle in expansion_map.get("follow_up_angles") or []:
                question = str(angle.get("question") or "").strip()
                if not question or question.lower() in existing:
                    continue
                if len(created) >= limit:
                    return {"stage": "expansion-questions-seeded", "created": created}
                criteria = (
                    "Use the parent research only as context; establish this narrower question "
                    "with at least two independent, traceable sources. Do not infer a claim the "
                    "new sources do not support."
                )
                try:
                    entry = curiosity.raise_question(
                        question, criteria, priority=4, budget=3,
                        tags=["content-expansion", str(expansion_map.get("family") or "general"), f"parent-root:{expansion_map.get('root_question_id')}"],
                        source=self.SOURCE,
                    )
                except ValueError:
                    return {"stage": "expansion-queue-full-preserved", "created": created}
                created.append(entry)
                existing.add(question.lower())
        return {"stage": "expansion-questions-seeded" if created else "no-pending-expansion-questions", "created": created}

    def snapshot(self):
        maps = self.maps()
        return {
            "source_packages": len(maps),
            "planned_follow_ups": sum(len(item.get("follow_up_angles") or []) for item in maps),
            "planned_creator_episodes": sum(
                int((item.get("creator_series_summary") or {}).get(
                    "planned_episode_count", 1 + len(item.get("follow_up_angles") or [])
                ))
                for item in maps
            ),
            "rule": "Follow-up angles are preserved, but each one independently earns evidence before production.",
        }
