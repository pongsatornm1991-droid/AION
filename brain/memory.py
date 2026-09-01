from pathlib import Path
from datetime import datetime
import re
import uuid


class MemoryEngine:

    MEMORY_TYPES = {
        "experience",
        "observation",
        "lesson",
        "belief",
        "decision",
        "semantic",
        "question",
        "goal",
        "experiment",
        "action",
    }

    def __init__(self, root="memory"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    def remember(
        self,
        category: str,
        content: str,
        memory_type: str = "experience",
        source: str = "aion",
        importance: int = 3,
        tags: list = None,
        related: list = None,
    ):
        """
        Save a structured memory to a Markdown file.

        Returns:
            dict describing the saved memory, or
            dict with duplicate=True if an equivalent memory exists.
        """

        memory_type = memory_type.lower().strip()

        if memory_type not in self.MEMORY_TYPES:
            raise ValueError(
                f"Unknown memory type: {memory_type}"
            )

        if not isinstance(importance, int):
            raise TypeError(
                "Importance must be an integer."
            )

        if not 1 <= importance <= 5:
            raise ValueError(
                "Importance must be between 1 and 5."
            )

        content = str(content).strip()

        if not content:
            raise ValueError(
                "Memory content cannot be empty."
            )

        # Prevent accidental exact duplicates.
        if self.is_duplicate(
            category=category,
            content=content,
            memory_type=memory_type,
            source=source,
        ):
            return {
                "saved": False,
                "duplicate": True,
                "category": category,
                "type": memory_type,
                "source": source,
                "importance": importance,
            }

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # A stable, collision-free identifier separate from the
        # human-readable timestamp header. Callers (DecisionHistory,
        # move()) must match entries by this id, never by timestamp
        # text, since two entries can share the same second.
        entry_id = uuid.uuid4().hex[:12]

        tags = self._normalize_list(tags)
        related = self._normalize_list(related)

        filename = self.root / f"{category}.md"

        header_lines = [
            f"ID: {entry_id}",
            f"TYPE: {memory_type}",
            f"SOURCE: {source}",
            f"IMPORTANCE: {importance}",
        ]

        if tags:
            header_lines.append(f"TAGS: {', '.join(tags)}")

        if related:
            header_lines.append(f"RELATED: {', '.join(related)}")

        with open(filename, "a", encoding="utf-8") as file:
            file.write(
                f"\n## {timestamp}\n\n"
                + "\n".join(header_lines)
                + f"\n\n{content}\n\n"
            )

        return {
            "saved": True,
            "duplicate": False,
            "id": entry_id,
            "timestamp": timestamp,
            "category": category,
            "type": memory_type,
            "source": source,
            "importance": importance,
            "tags": tags,
            "related": related,
            "content": content,
        }

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------

    def read(self, category: str):
        """
        Read a memory category.
        """

        filename = self.root / f"{category}.md"

        if not filename.exists():
            return ""

        return filename.read_text(
            encoding="utf-8"
        )

    # ---------------------------------------------------------
    # PARSE
    # ---------------------------------------------------------

    def all(self, category: str):
        """
        Return all memories in a category as structured dictionaries.
        """

        text = self.read(category)

        if not text:
            return []

        raw_entries = text.split("\n## ")

        memories = []

        for raw in raw_entries:

            raw = raw.strip()

            if not raw:
                continue

            lines = [
                line.strip()
                for line in raw.splitlines()
                if line.strip()
            ]

            if not lines:
                continue

            timestamp = lines[0]

            # Legacy entries saved before the ID field existed have
            # no ID line; the timestamp is the only identifier they
            # ever had, so it remains their id.
            entry_id = timestamp
            memory_type = "legacy"
            source = "unknown"
            importance = 1
            tags = []
            related = []

            content_start = 1

            while content_start < len(lines):

                line = lines[content_start]

                if line.startswith("ID:"):
                    entry_id = line.replace(
                        "ID:", "", 1
                    ).strip() or timestamp

                elif line.startswith("TYPE:"):
                    memory_type = line.replace(
                        "TYPE:", "", 1
                    ).strip()

                elif line.startswith("SOURCE:"):
                    source = line.replace(
                        "SOURCE:", "", 1
                    ).strip()

                elif line.startswith("IMPORTANCE:"):
                    raw_importance = line.replace(
                        "IMPORTANCE:", "", 1
                    ).strip()

                    try:
                        importance = int(
                            raw_importance
                        )
                    except ValueError:
                        importance = 1

                    importance = max(
                        1,
                        min(5, importance)
                    )

                elif line.startswith("TAGS:"):
                    tags = self._normalize_list(
                        line.replace("TAGS:", "", 1).split(",")
                    )

                elif line.startswith("RELATED:"):
                    related = self._normalize_list(
                        line.replace("RELATED:", "", 1).split(",")
                    )

                else:
                    break

                content_start += 1

            content = "\n".join(
                lines[content_start:]
            ).strip()

            memories.append({
                "id": entry_id,
                "timestamp": timestamp,
                "type": memory_type,
                "source": source,
                "importance": importance,
                "tags": tags,
                "related": related,
                "content": content,
            })

        return memories

    # ---------------------------------------------------------
    # RECENT
    # ---------------------------------------------------------

    def recent(
        self,
        category: str,
        limit=5,
    ):
        """
        Return recent memories.
        """

        if limit < 1:
            return []

        memories = self.all(category)

        return memories[-limit:]

    # ---------------------------------------------------------
    # IMPORTANT
    # ---------------------------------------------------------

    def important(
        self,
        category: str,
        minimum=4,
        limit=5,
    ):
        """
        Return the most important memories.
        """

        if not 1 <= minimum <= 5:
            raise ValueError(
                "Minimum importance must be between 1 and 5."
            )

        if limit < 1:
            return []

        memories = self.all(category)

        important_memories = [
            memory
            for memory in memories
            if memory["importance"] >= minimum
        ]

        important_memories.sort(
            key=lambda memory: (
                memory["importance"],
                memory["timestamp"],
            ),
            reverse=True,
        )

        return important_memories[:limit]

    # ---------------------------------------------------------
    # NORMALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def normalize_content(content: str):
        """
        Normalize text for duplicate detection.

        Removes:
        - case differences
        - repeated whitespace
        - minor punctuation differences
        """

        content = str(content).lower().strip()

        content = re.sub(
            r"\s+",
            " ",
            content,
        )

        content = re.sub(
            r"[^\w\s]",
            "",
            content,
        )

        return content

    @staticmethod
    def _normalize_list(values):
        """Clean a list of strings: strip, drop empties, de-duplicate,
        preserve order. Accepts None. Used for tags and related-ids."""

        if not values:
            return []

        normalized = []

        for value in values:
            value = str(value).strip()

            if value and value not in normalized:
                normalized.append(value)

        return normalized

    # ---------------------------------------------------------
    # DUPLICATE DETECTION
    # ---------------------------------------------------------

    def is_duplicate(
        self,
        category: str,
        content: str,
        memory_type: str = "experience",
        source: str = "aion",
    ):
        """
        Detect whether an equivalent memory already exists.

        Duplicate comparison uses:
        - category
        - memory type
        - source
        - normalized content
        """

        normalized = self.normalize_content(
            content
        )

        if not normalized:
            return False

        memories = self.all(category)

        for memory in memories:

            if memory["type"] != memory_type:
                continue

            if memory["source"] != source:
                continue

            existing = self.normalize_content(
                memory["content"]
            )

            if existing == normalized:
                return True

        return False

    # ---------------------------------------------------------
    # MOVE
    # ---------------------------------------------------------

    def move(
        self,
        source_category: str,
        target_category: str,
        entry_id: str,
        content: str = None,
        importance: int = None,
    ):
        """Move one memory entry to another category.

        entry_id must identify exactly one entry in the source
        category. Entries are matched by their stable id (falling
        back to timestamp only for legacy entries saved before the
        id field existed) rather than by timestamp text, since two
        entries can otherwise share the same second. This makes
        category transitions, such as promoting a verified decision,
        explicit and auditable.
        """

        source_entries = self.all(source_category)
        matches = [
            entry
            for entry in source_entries
            if entry["id"] == entry_id
        ]

        if not matches:
            raise ValueError(
                "No memory entry matches the supplied id."
            )

        if len(matches) > 1:
            raise ValueError(
                "More than one memory entry matches the supplied id."
            )

        selected = matches[0].copy()

        if content is not None:
            selected["content"] = str(content).strip()

        if importance is not None:
            if not isinstance(importance, int) or not 1 <= importance <= 5:
                raise ValueError(
                    "Importance must be an integer between 1 and 5."
                )
            selected["importance"] = importance

        remaining = [
            entry
            for entry in source_entries
            if entry is not matches[0]
        ]

        target_entries = self.all(target_category)
        target_entries.append(selected)

        self._write_entries(target_category, target_entries)
        self._write_entries(source_category, remaining)

        return selected

    def update(self, category: str, entry_id: str, content: str = None):
        """Update one memory entry's content without changing its identity.

        Long-running external actions use this to checkpoint a partial result
        (for example, an Instagram Reel published while Facebook is still
        retrying) so a later run cannot repeat the completed side effect.
        """
        entries = self.all(category)
        matches = [entry for entry in entries if entry["id"] == entry_id]
        if len(matches) != 1:
            raise ValueError("No unique memory entry matches the supplied id.")
        if content is not None:
            cleaned = str(content).strip()
            if not cleaned:
                raise ValueError("Memory content cannot be empty.")
            matches[0]["content"] = cleaned
        self._write_entries(category, entries)
        return matches[0]

    def _write_entries(self, category: str, entries: list):
        """Rewrite one memory category from structured entries."""

        filename = self.root / f"{category}.md"
        parts = []

        for entry in entries:

            header_lines = [
                f"ID: {entry['id']}",
                f"TYPE: {entry['type']}",
                f"SOURCE: {entry['source']}",
                f"IMPORTANCE: {entry['importance']}",
            ]

            entry_tags = self._normalize_list(entry.get("tags", []))
            entry_related = self._normalize_list(entry.get("related", []))

            if entry_tags:
                header_lines.append(f"TAGS: {', '.join(entry_tags)}")

            if entry_related:
                header_lines.append(f"RELATED: {', '.join(entry_related)}")

            parts.append(
                f"\n## {entry['timestamp']}\n\n"
                + "\n".join(header_lines)
                + f"\n\n{entry['content'].strip()}\n"
            )

        filename.write_text(
            "".join(parts),
            encoding="utf-8",
        )

    # ---------------------------------------------------------
    # QUALITY
    # ---------------------------------------------------------

    def quality(self, memory):
        """
        Estimate memory quality from 0 to 5.

        Quality considers:
        - content length
        - metadata validity
        - specificity
        - importance
        """

        if not isinstance(memory, dict):
            return 0

        content = str(
            memory.get("content", "")
        ).strip()

        if not content:
            return 0

        score = 0

        # Content exists.
        score += 1

        # Meaningful length.
        if len(content) >= 50:
            score += 1

        # Structured content.
        if any(
            marker in content
            for marker in [
                "FACT",
                "LESSON",
                "DECISION",
                "UNCERTAINT",
                "EVIDENCE",
                "OBJECTIVE",
            ]
        ):
            score += 1

        # Valid memory type.
        if memory.get("type") in self.MEMORY_TYPES:
            score += 1

        # Importance contributes to quality.
        importance = memory.get(
            "importance",
            1,
        )

        if isinstance(importance, int):
            if importance >= 4:
                score += 1

        return min(5, score)

    # ---------------------------------------------------------
    # QUALITY REPORT
    # ---------------------------------------------------------

    def quality_report(self, category: str):
        """
        Return quality statistics for a memory category.
        """

        memories = self.all(category)

        if not memories:
            return {
                "total": 0,
                "average_quality": 0.0,
                "low_quality": 0,
                "high_quality": 0,
            }

        qualities = [
            self.quality(memory)
            for memory in memories
        ]

        average = sum(qualities) / len(
            qualities
        )

        return {
            "total": len(memories),
            "average_quality": round(
                average,
                2,
            ),
            "low_quality": sum(
                1
                for score in qualities
                if score <= 2
            ),
            "high_quality": sum(
                1
                for score in qualities
                if score >= 4
            ),
        }

    # ---------------------------------------------------------
    # STATS
    # ---------------------------------------------------------

    def stats(self, category: str):
        """
        Return memory statistics.
        """

        memories = self.all(category)

        importance = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
        }

        types = {}

        for memory in memories:

            level = memory["importance"]

            if level not in importance:
                importance[level] = 0

            importance[level] += 1

            memory_type = memory["type"]

            types[memory_type] = (
                types.get(memory_type, 0) + 1
            )

        return {
            "total": len(memories),
            "importance": importance,
            "types": types,
        }

    # ---------------------------------------------------------
    # TAGS & RELATED-MEMORY RETRIEVAL
    # ---------------------------------------------------------

    def add_tags(self, category: str, entry_id: str, tags: list):
        """Attach additional tags to an existing entry (retroactive
        tagging). Merges with any tags the entry already has rather
        than replacing them. Returns the updated entry."""

        entries = self.all(category)
        matches = [entry for entry in entries if entry["id"] == entry_id]

        if not matches:
            raise ValueError(
                "No memory entry matches the supplied id."
            )

        if len(matches) > 1:
            raise ValueError(
                "More than one memory entry matches the supplied id."
            )

        selected = matches[0]
        selected["tags"] = self._normalize_list(
            list(selected.get("tags", [])) + list(tags or [])
        )

        self._write_entries(category, entries)

        return selected

    def by_tag(self, category: str, tag: str):
        """Return all entries in a category carrying the given tag
        (case-insensitive)."""

        tag = str(tag).strip().lower()

        if not tag:
            return []

        return [
            entry
            for entry in self.all(category)
            if tag in [existing.lower() for existing in entry.get("tags", [])]
        ]

    def related_entries(self, category: str, entry_id: str, limit=5):
        """Find other entries in the same category related to one
        entry, purely from stored metadata — no AI call involved, so
        this is deterministic and always works offline.

        Entries explicitly listed in the source entry's RELATED field
        are returned first (in stored order), then any remaining
        entries are ranked by number of shared tags (highest first).
        """

        entries = self.all(category)
        by_id = {entry["id"]: entry for entry in entries}

        source = by_id.get(entry_id)

        if source is None:
            raise ValueError(
                "No memory entry matches the supplied id."
            )

        ordered = []
        seen = {entry_id}

        for related_id in source.get("related", []):
            candidate = by_id.get(related_id)

            if candidate is not None and candidate["id"] not in seen:
                ordered.append(candidate)
                seen.add(candidate["id"])

        source_tags = set(
            tag.lower() for tag in source.get("tags", [])
        )

        if source_tags:
            scored = []

            for entry in entries:
                if entry["id"] in seen:
                    continue

                entry_tags = set(
                    tag.lower() for tag in entry.get("tags", [])
                )
                overlap = len(source_tags & entry_tags)

                if overlap > 0:
                    scored.append((overlap, entry))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            ordered.extend(entry for _, entry in scored)

        return ordered[:limit]
