"""Low-cost autonomous initiative when AION has no question to pursue.

This is deliberately a chooser, not a pretend inner life: it makes the
reason for each new inquiry inspectable and creates no model request itself.
The existing evidence-aware learning cycle does the research afterwards.
"""

from brain.curiosity import CuriosityEngine


class AutonomousInitiative:
    """Seed one evidence-bound inquiry from the least explored curiosity area."""

    CATEGORY = "autonomous_initiatives"
    SOURCE = "aion-autonomous-initiative"

    # These are starting lenses, not an allow-list. The constitution retains
    # room for novel questions raised later from real observations.
    INQUIRIES = (
        ("identity_and_memory", "How do memory and revision practices help an intelligent system remain accountable over time?"),
        ("humans_and_community", "What makes people choose to join a new learning community and keep contributing to it?"),
        ("thai_context", "What approaches make complex ideas accessible to Thai-speaking audiences without oversimplifying them?"),
        ("intelligence_and_learning", "What practices make an AI-assisted explanation more reliable and easier for people to verify?"),
        ("creative_expression", "How can a recurring character make an educational story more memorable without replacing evidence with spectacle?"),
        ("shared_future", "What questions help people discuss technology's effects on society with both hope and caution?"),
        ("world_and_science", "How can a science story connect a verified observation to an everyday question people genuinely notice?"),
    )

    # The daily Shorts promise needs a small, evidence-friendly lane when the
    # release buffer is low.  These are deliberately concrete questions with
    # a clear visual idea, not a replacement for AION's longer-running open
    # research.  Each one is compatible with an implemented specialist source
    # adapter as well as the orientation source, so a recovery run does not
    # repeatedly spend its limited retrieval budget on an unrelated subject.
    RECOVERY_INQUIRIES = (
        (
            "insect-science",
            "How do honeybees, an insect, tell their nestmates where food is?",
            "Show one bee's dance changing direction as a simple map.",
        ),
        (
            "plant-science",
            "How do plants know which way to grow toward light?",
            "Show a seedling slowly bending toward one lamp.",
        ),
        (
            "animal-science",
            "Why do some animals change colour to blend into their surroundings?",
            "Show one animal against two clearly different backgrounds.",
        ),
        (
            "brain-science",
            "Why do people get goosebumps even when they are not cold?",
            "Show tiny muscles lifting hairs beside a simple emotion cue.",
        ),
        (
            "ocean-science",
            "How do coral animals build a reef over time?",
            "Show many tiny animals adding one layer at a time.",
        ),
        (
            "weather-science",
            "Why can lightning be seen before thunder is heard?",
            "Show one lightning flash and two travelling waves racing toward a listener.",
        ),
        (
            "water-science",
            "Why do raindrops look round as they fall?",
            "Show surface tension pulling one falling drop into a rounded shape.",
        ),
        (
            "earth-science",
            "Why do some rocks have layers like pages in a book?",
            "Show grains settling one thin layer at a time beneath clear water.",
        ),
        (
            "space-science",
            "Why does the Moon appear to change shape during a month?",
            "Show the Sun lighting half a small Moon as it travels around Earth.",
        ),
        (
            "sound-science",
            "How can a guitar string make different musical notes?",
            "Show a short and a long string vibrating at visibly different speeds.",
        ),
        (
            "light-science",
            "Why does a shadow change length during the day?",
            "Show one lamp-like Sun moving across a tiny street and stretching a shadow.",
        ),
        (
            "body-science",
            "Why does breathing become faster when we run?",
            "Show a runner and a simple oxygen delivery route becoming busier.",
        ),
        (
            "food-science",
            "Why does bread rise while it bakes?",
            "Show tiny gas bubbles expanding inside one piece of dough.",
        ),
        (
            "materials-science",
            "Why can a paper clip stick to a magnet?",
            "Show a magnet lining up tiny arrows inside one paper clip.",
        ),
        (
            "plant-science-2",
            "How do seeds travel away from their parent plant?",
            "Show one seed using wind, water, and an animal ride in three simple beats.",
        ),
        (
            "animal-science-2",
            "Why do birds have different beak shapes?",
            "Show three beaks matching three clearly different kinds of food.",
        ),
        (
            "ocean-science-2",
            "Why do tides rise and fall at the shore?",
            "Show the Moon pulling two gentle ocean bulges around Earth.",
        ),
        (
            "climate-science",
            "Why are cities often warmer than nearby countryside at night?",
            "Show buildings holding heat while trees and fields cool more quickly.",
        ),
        (
            "history-engineering",
            "How did ancient people measure time using shadows?",
            "Show a simple sundial shadow moving across marked stones.",
        ),
        (
            "everyday-physics",
            "Why does a bicycle stay upright more easily when it is moving?",
            "Show a slow bicycle wobbling and a moving bicycle following a smooth path.",
        ),
        (
            "chemistry",
            "Why does ice float on liquid water?",
            "Show an open ice crystal structure taking more space than liquid water.",
        ),
    )
    RECOVERY_TAG = "shorts-recovery"
    # Keep research ahead of production.  This is deliberately a reserve of
    # research questions, not a promise of 21 completed episodes: each item
    # still needs two independent, traceable sources before it can reach the
    # creator queue.
    EVIDENCE_RESERVE_TARGET = 21
    RECOVERY_SEED_BATCH = 5

    def __init__(self, memory, curiosity=None):
        self.memory = memory
        self.curiosity = curiosity or CuriosityEngine(memory)

    def _used_domains(self):
        used = set()
        for entry in self.memory.all(self.CATEGORY):
            used.update(entry.get("tags") or [])
        return used

    def initiate_recovery_batch(self, missing=0, target=None, seed_limit=None):
        """Maintain a bounded, distinct evidence-research reserve.

        Previously a release shortage opened only one recovery question.  The
        next Short then had to wait for that single question to complete,
        even though the downstream story and Studio shifts can safely process
        a bounded batch.  Seed up to five *different* questions per learning
        pass and keep at most 21 open reserve questions.  This is an upstream
        planning queue only; it never marks evidence as qualified or creates
        media.
        """
        try:
            missing = int(missing)
        except (TypeError, ValueError):
            missing = 0
        if missing <= 0:
            return {"stage": "buffer-healthy", "created": False, "questions": []}

        target = self.EVIDENCE_RESERVE_TARGET if target is None else max(1, int(target))
        seed_limit = self.RECOVERY_SEED_BATCH if seed_limit is None else max(1, int(seed_limit))

        recovery_questions = self.curiosity.open_questions(topic=self.RECOVERY_TAG)
        active = [entry for entry in recovery_questions if not entry.get("budget_exhausted")]
        if len(active) >= target:
            return {
                "stage": "recovery-reserve-active",
                "created": False,
                "questions": active[:seed_limit],
                "active_count": len(active),
                "target": target,
            }

        # Include historical recovery decisions too. An answered, exhausted,
        # or evidence-rejected recovery question is deliberately preserved in
        # memory, so looking only at *currently open* questions would reopen
        # the same topic on the next low-buffer tick.
        attempted_domains = self._used_domains() | {
            tag for entry in recovery_questions for tag in (entry.get("tags") or [])
        }
        open_statements = {
            str(entry.get("statement") or "").strip().lower()
            for entry in self.curiosity.open_questions()
        }
        criteria = (
            "Record observations from at least two independent credible sources "
            "with stable URLs. Explain one verified mechanism in language suitable "
            "for a 50–60 second factual Short, use the planned visual metaphor, and "
            "state any unresolved uncertainty before closing the question."
        )
        candidates = [
            candidate for candidate in self.RECOVERY_INQUIRIES
            if candidate[0] not in attempted_domains
            and candidate[1].lower() not in open_statements
        ]
        # After every designed reserve topic has been tried, retain the
        # historical record and stop rather than silently recycling the first
        # question as if it were new evidence.
        to_create = min(seed_limit, max(0, target - len(active)), len(candidates))
        created = []
        created_domains = []
        created_visual_metaphors = []
        for domain, question, visual_metaphor in candidates[:to_create]:
            entry = self.curiosity.raise_question(
                question,
                criteria,
                priority=5,
                budget=3,
                tags=[self.RECOVERY_TAG, "shorts-first", domain],
                source=self.SOURCE,
            )
            self.memory.remember(
                self.CATEGORY,
                f"AION opened recovery inquiry {entry.get('id')} because the Shorts "
                f"buffer is short by {missing}. Domain: {domain}. Visual: {visual_metaphor}",
                memory_type="decision",
                source=self.SOURCE,
                importance=5,
                tags=[self.RECOVERY_TAG, domain],
                related=[entry.get("id")],
            )
            created.append(entry)
            created_domains.append(domain)
            created_visual_metaphors.append(visual_metaphor)

        # Finish the oldest live reserve questions first.  That gives the
        # earliest evidence pair a chance to reach the story queue on the
        # very next pass while newer questions are already waiting behind it.
        selected = (active + created)[:seed_limit]
        return {
            "stage": "seeded-recovery-reserve" if created else "recovery-reserve-exhausted",
            "created": bool(created),
            "created_count": len(created),
            "created_domains": created_domains,
            "created_visual_metaphors": created_visual_metaphors,
            "questions": selected,
            "active_count": len(active) + len(created),
            "target": target,
        }

    def initiate_recovery_once(self, missing=0):
        """Compatibility wrapper for callers that need one recovery question."""
        report = self.initiate_recovery_batch(missing, target=1, seed_limit=1)
        questions = report.get("questions") or []
        if report.get("stage") == "seeded-recovery-reserve":
            report["stage"] = "seeded-recovery-question"
        elif report.get("stage") == "recovery-reserve-active":
            report["stage"] = "recovery-question-active"
        report["question"] = questions[0] if questions else None
        if report.get("created_domains"):
            report["domain"] = report["created_domains"][0]
        if report.get("created_visual_metaphors"):
            report["visual_metaphor"] = report["created_visual_metaphors"][0]
        return report

    def initiate_once(self):
        """Create exactly one inquiry only when the real queue is empty."""
        open_questions = self.curiosity.open_questions(limit=1)
        if open_questions:
            return {"stage": "question-already-open", "created": False}

        used = self._used_domains()
        domain, question = next(
            ((domain, question) for domain, question in self.INQUIRIES if domain not in used),
            self.INQUIRIES[0],
        )
        criteria = (
            "Record observations from at least two independent credible sources, "
            "cite both, and state any unresolved uncertainty before closing the question."
        )
        created = self.curiosity.raise_question(
            question, criteria, priority=3, budget=3,
            tags=["autonomous-initiative", "knowledge-gap", domain],
            source=self.SOURCE,
        )
        self.memory.remember(
            self.CATEGORY,
            f"AION selected the least-yet-explored inquiry lens: {domain}. "
            f"It opened question {created.get('id')} with evidence requirements.",
            memory_type="decision", source=self.SOURCE, importance=3,
            tags=["autonomous-initiative", domain], related=[created.get("id")],
        )
        return {"stage": "seeded-question", "created": True, "domain": domain, "question": created}
