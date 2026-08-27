from pathlib import Path
from datetime import datetime


class MemoryEngine:
    def __init__(self, root="memory"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def remember(self, category: str, content: str):
        """
        Save a new memory to a Markdown file.
        """

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        filename = self.root / f"{category}.md"

        with open(filename, "a", encoding="utf-8") as file:
            file.write(
                f"\n## {timestamp}\n\n"
                f"{content.strip()}\n\n"
            )

    def read(self, category: str):
        """
        Read a memory category.
        """

        filename = self.root / f"{category}.md"

        if not filename.exists():
            return ""

        return filename.read_text(encoding="utf-8")

    def recent(self, category: str, limit=5):
        """
        Return the latest memory entries.
        """

        text = self.read(category)

        if not text:
            return []

        entries = text.split("\n## ")

        entries = [
            entry.strip()
            for entry in entries
            if entry.strip()
        ]

        return entries[-limit:]
