from brain.memory import MemoryEngine
from brain.identity import Identity


class CognitiveState:

    def __init__(self):
        self.memory = MemoryEngine()
        self.identity = Identity()

    def summary(self):
        experiences = self.memory.all("experiences")
        lessons = self.memory.all("lessons")

        recent_memories = self.memory.recent(
            "experiences",
            limit=5,
        )

        important_memories = self.memory.important(
            "experiences",
            minimum=4,
            limit=5,
        )

        important_lessons = self.memory.important(
            "lessons",
            minimum=4,
            limit=5,
        )

        stats = self.memory.stats("experiences")

        return {
            "total_memories": len(experiences),
            "recent_memories": len(recent_memories),
            "important_memories": len(important_memories),
            "memory_types": stats["types"],
            "importance_distribution": stats["importance"],
            "total_lessons": len(lessons),
            "important_lessons": len(important_lessons),
        }

    def build(self):
        identity = self.identity.load()

        experiences = self.memory.all(
            "experiences"
        )

        recent_memories = self.memory.recent(
            "experiences",
            limit=5,
        )

        important_memories = self.memory.important(
            "experiences",
            minimum=4,
            limit=5,
        )

        lessons = self.memory.recent(
            "lessons",
            limit=5,
        )

        important_lessons = self.memory.important(
            "lessons",
            minimum=4,
            limit=5,
        )

        experience_stats = self.memory.stats(
            "experiences"
        )

        lesson_stats = self.memory.stats(
            "lessons"
        )

        return {
            "identity": identity,

            "memory": {
                "total": len(experiences),
                "recent": recent_memories,
                "important": important_memories,
                "types": experience_stats["types"],
                "importance": experience_stats["importance"],
            },

            "learning": {
                "total": len(lessons),
                "recent": lessons,
                "important": important_lessons,
                "types": lesson_stats["types"],
                "importance": lesson_stats["importance"],
            },
        }