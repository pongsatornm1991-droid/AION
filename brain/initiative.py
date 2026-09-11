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

    def __init__(self, memory, curiosity=None):
        self.memory = memory
        self.curiosity = curiosity or CuriosityEngine(memory)

    def _used_domains(self):
        used = set()
        for entry in self.memory.all(self.CATEGORY):
            used.update(entry.get("tags") or [])
        return used

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
