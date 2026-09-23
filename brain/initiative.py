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
    )
    RECOVERY_TAG = "shorts-recovery"

    def __init__(self, memory, curiosity=None):
        self.memory = memory
        self.curiosity = curiosity or CuriosityEngine(memory)

    def _used_domains(self):
        used = set()
        for entry in self.memory.all(self.CATEGORY):
            used.update(entry.get("tags") or [])
        return used

    def initiate_recovery_once(self, missing=0):
        """Keep an evidence-friendly Short moving while the buffer is low.

        This never deletes or demotes the normal research queue.  It opens at
        most one high-priority recovery inquiry, reuses an active one on the
        next run, and moves on only after its bounded attempt budget is spent.
        That makes the recovery path visible and auditable instead of quietly
        discarding a difficult question or silently recycling an old episode.
        """
        try:
            missing = int(missing)
        except (TypeError, ValueError):
            missing = 0
        if missing <= 0:
            return {"stage": "buffer-healthy", "created": False}

        recovery_questions = self.curiosity.open_questions(topic=self.RECOVERY_TAG)
        active = next(
            (entry for entry in recovery_questions if not entry.get("budget_exhausted")),
            None,
        )
        if active:
            return {
                "stage": "recovery-question-active",
                "created": False,
                "question": active,
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
        domain, question, visual_metaphor = next(
            (
                candidate for candidate in self.RECOVERY_INQUIRIES
                if candidate[0] not in attempted_domains
                and candidate[1].lower() not in open_statements
            ),
            self.RECOVERY_INQUIRIES[0],
        )
        criteria = (
            "Record observations from at least two independent credible sources "
            "with stable URLs. Explain one verified mechanism in language suitable "
            "for a 50–60 second factual Short, use the planned visual metaphor, and "
            "state any unresolved uncertainty before closing the question."
        )
        created = self.curiosity.raise_question(
            question,
            criteria,
            priority=5,
            budget=3,
            tags=[self.RECOVERY_TAG, "shorts-first", domain],
            source=self.SOURCE,
        )
        self.memory.remember(
            self.CATEGORY,
            f"AION opened recovery inquiry {created.get('id')} because the Shorts "
            f"buffer is short by {missing}. Domain: {domain}. Visual: {visual_metaphor}",
            memory_type="decision",
            source=self.SOURCE,
            importance=5,
            tags=[self.RECOVERY_TAG, domain],
            related=[created.get("id")],
        )
        return {
            "stage": "seeded-recovery-question",
            "created": True,
            "domain": domain,
            "visual_metaphor": visual_metaphor,
            "question": created,
        }

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
