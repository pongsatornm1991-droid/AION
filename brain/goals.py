from .bounded_tracker import BoundedItemTracker


class GoalEngine(BoundedItemTracker):
    """AION's bounded set of active goals.

    Every goal must state its own completion criteria up front, and
    can only be marked complete with cited evidence of the outcome —
    a goal is never "done" just because a provider says so. Goals and
    questions (CuriosityEngine) intentionally share the same
    mechanics (BoundedItemTracker): open with explicit criteria and a
    budget, log attempts over time, resolve only with evidence, or
    abandon with a reason — never edited in place, full history always
    on disk.
    """

    CATEGORY = "goals"
    MEMORY_TYPE = "goal"
    ITEM_LABEL = "Goal"
    RESOLUTION_LABEL = "Outcome"
    DEFAULT_MAX_OPEN = 10
    DEFAULT_BUDGET = 5

    def set_goal(
        self,
        description,
        completion_criteria,
        priority=3,
        budget=None,
        tags=None,
        source="aion",
    ):
        return self.open_item(
            statement=description,
            completion_criteria=completion_criteria,
            priority=priority,
            budget=budget,
            tags=tags,
            source=source,
        )

    def complete_goal(self, entry_id, outcome, evidence):
        return self.resolve_item(entry_id, outcome, evidence)

    def abandon_goal(self, entry_id, reason):
        return self.abandon_item(entry_id, reason)

    def active_goals(self, topic: str = None, limit: int = None):
        return self.open_items(topic=topic, limit=limit)
