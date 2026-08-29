from .memory import MemoryEngine


class MemoryInspector:

    def __init__(self):
        self.memory = MemoryEngine()

    def inspect(self, category="experiences"):
        stats = self.memory.stats(category)

        print("=" * 60)
        print("AION MEMORY INSPECTOR")
        print("=" * 60)

        print(f"\nCategory: {category}")
        print(f"Total memories: {stats['total']}")

        print("\nImportance:")
        for level in range(1, 6):
            count = stats["importance"].get(level, 0)
            print(f"  {level} → {count}")

        print("\nMemory types:")

        if stats["types"]:
            for memory_type, count in sorted(
                stats["types"].items()
            ):
                print(f"  {memory_type:<12} → {count}")
        else:
            print("  None")

        important = self.memory.important(
            category,
            minimum=4,
            limit=5
        )

        print("\nImportant memories:")
        print(f"  {len(important)}")

        print("\n" + "=" * 60)

        return stats