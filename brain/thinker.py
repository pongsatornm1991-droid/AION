from .identity import Identity
from .memory import MemoryEngine


class Thinker:

    def __init__(self):
        self.identity = Identity()
        self.memory = MemoryEngine()

    def build_context(self):

        identity = self.identity.load()

        recent_memories = self.memory.recent(
            "experiences",
            limit=5,
        )

        important_memories = self.memory.important(
            "experiences",
            minimum=4,
            limit=5,
        )

        recent_lessons = self.memory.recent(
            "lessons",
            limit=5,
        )

        important_lessons = self.memory.important(
            "lessons",
            minimum=4,
            limit=5,
        )

        accepted_decisions = self.memory.recent(
            "decisions_accepted",
            limit=3,
        )

        pending_decisions = self.memory.recent(
            "decisions_pending_verification",
            limit=3,
        )

        context = {
            "identity": identity,
            "recent_memories": recent_memories,
            "important_memories": important_memories,
            "recent_lessons": recent_lessons,
            "important_lessons": important_lessons,
            "accepted_decisions": accepted_decisions,
            "pending_decisions": pending_decisions,
        }

        return context
