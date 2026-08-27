from .identity import Identity
from .memory import MemoryEngine


class Thinker:

    def __init__(self):
        self.identity = Identity()
        self.memory = MemoryEngine()

    def build_context(self):

        identity = self.identity.load()

        memories = self.memory.recent(
            "experiences",
            limit=5
        )

        context = {
            "identity": identity,
            "recent_memories": memories,
        }

        return context
