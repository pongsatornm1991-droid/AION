from .bounded_tracker import BoundedItemTracker


class CuriosityEngine(BoundedItemTracker):
    """AION's bounded set of open questions.

    Every question must state its own completion criteria up front —
    what would actually count as having answered it — and can only be
    marked answered with cited evidence, the same evidence requirement
    BeliefSystem.form_belief() enforces. This is deliberate: an
    answered question is exactly the kind of claim a belief should be
    built from, so the two components share a discipline, not just a
    coincidence of shape.
    """

    CATEGORY = "questions"
    MEMORY_TYPE = "question"
    ITEM_LABEL = "Question"
    RESOLUTION_LABEL = "Answer"
    DEFAULT_MAX_OPEN = 10
    DEFAULT_BUDGET = 3

    def raise_question(
        self,
        question,
        completion_criteria,
        priority=3,
        budget=None,
        tags=None,
        source="aion",
    ):
        return self.open_item(
            statement=question,
            completion_criteria=completion_criteria,
            priority=priority,
            budget=budget,
            tags=tags,
            source=source,
        )

    def answer_question(self, entry_id, answer, evidence):
        return self.resolve_item(entry_id, answer, evidence)

    def abandon_question(self, entry_id, reason):
        return self.abandon_item(entry_id, reason)

    def open_questions(self, topic: str = None, limit: int = None):
        return self.open_items(topic=topic, limit=limit)
