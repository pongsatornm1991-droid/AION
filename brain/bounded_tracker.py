import re


class BoundedItemTracker:
    """Generic base for a bounded, evidence-gated open-item tracker.

    AION's curiosity (open questions) and goal-selection (active
    goals) share exactly one shape: raise/open an item with an
    explicit, stated completion criteria and a budget, work on it over
    time, and only ever resolve it with cited evidence — the provider
    is never trusted to decide on its own that something is "done".
    This class implements that shape once; CuriosityEngine and
    GoalEngine are thin, differently-labeled subclasses of it.

    Bounded in two independent ways:
    - System-wide: only `max_open` items may be open at once.
      open_item() refuses a new one past that cap — something must be
      resolved or abandoned first.
    - Per-item: each item carries its own attempt `budget`. Nothing
      is auto-abandoned when the budget is used up (that would be a
      silent, unreviewed data loss); it is only surfaced as
      `budget_exhausted` for whoever is reviewing open items to act on.

    Nothing is ever edited in place. record_attempt() and
    resolve_item() each write a brand-new entry (a "Predecessor:"
    field, mirrored in the memory engine's `related` metadata) and tag
    the previous entry "superseded" — the full history stays on disk
    and auditable via history(). abandon_item() never creates a
    replacement; it tags the item "abandoned" and logs why as a
    companion lessons entry, the same pattern BeliefSystem uses for
    retraction.
    """

    CATEGORY = "items"
    MEMORY_TYPE = "item"
    ITEM_LABEL = "Item"
    RESOLUTION_LABEL = "Resolution"
    DEFAULT_MAX_OPEN = 10
    DEFAULT_BUDGET = 3

    _EVIDENCE_ID_PATTERN = re.compile(r"^(.*?)\(id:\s*(.+?)\)\s*$")

    def __init__(self, memory, category=None, max_open=None):
        self.memory = memory
        self.category = category or self.CATEGORY
        self.max_open = (
            self.DEFAULT_MAX_OPEN if max_open is None else max_open
        )

    # ---------------------------------------------------------
    # OPEN
    # ---------------------------------------------------------

    def open_item(
        self,
        statement,
        completion_criteria,
        priority=3,
        budget=None,
        tags=None,
        source="aion",
    ):
        statement = str(statement).strip()

        if not statement:
            raise ValueError(f"{self.ITEM_LABEL} cannot be empty.")

        completion_criteria = str(completion_criteria).strip()

        if not completion_criteria:
            raise ValueError(
                "Completion criteria is required — an item cannot be "
                "opened without an explicit, bounded definition of "
                "done."
            )

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or not 1 <= priority <= 5
        ):
            raise ValueError(
                "Priority must be an integer between 1 and 5."
            )

        budget = self.DEFAULT_BUDGET if budget is None else budget

        if (
            not isinstance(budget, int)
            or isinstance(budget, bool)
            or budget < 1
        ):
            raise ValueError("Budget must be a positive integer.")

        open_count = len(self.open_items())

        if open_count >= self.max_open:
            raise ValueError(
                f"Cannot open a new {self.ITEM_LABEL.lower()}: "
                f"{open_count} are already open "
                f"(max_open={self.max_open}). Resolve or abandon one "
                "first."
            )

        content = self._format_content(
            statement=statement,
            criteria=completion_criteria,
            budget=budget,
            attempts=0,
            predecessor=None,
            resolution=None,
            evidence=[],
            progress=[],
        )

        return self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=source,
            importance=priority,
            tags=tags,
        )

    # ---------------------------------------------------------
    # PROGRESS
    # ---------------------------------------------------------

    def record_attempt(self, entry_id, note=None):
        """Log one attempt/effort spent on this item. Writes a new
        entry (attempts + 1) superseding the current one; never edits
        in place. Refuses once the item is resolved or abandoned."""

        current = self._get(entry_id)

        if current is None:
            raise ValueError(
                f"No {self.ITEM_LABEL.lower()} matches the supplied id."
            )

        status = self.status_of(current)

        if status != "open":
            raise ValueError(
                f"Cannot record an attempt on a {status} "
                f"{self.ITEM_LABEL.lower()}."
            )

        parsed = self._parse_content(current["content"])
        progress = list(parsed["progress"])

        if note:
            progress.append(str(note).strip())

        content = self._format_content(
            statement=parsed["statement"],
            criteria=parsed["criteria"],
            budget=parsed["budget"],
            attempts=parsed["attempts"] + 1,
            predecessor=entry_id,
            resolution=None,
            evidence=parsed["evidence"],
            progress=progress,
        )

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=current.get("source", "aion"),
            importance=current["importance"],
            tags=current.get("tags", []),
            related=[entry_id],
        )

        self.memory.add_tags(self.category, entry_id, ["superseded"])

        return saved

    # ---------------------------------------------------------
    # RESOLVE
    # ---------------------------------------------------------

    def resolve_item(self, entry_id, resolution, evidence):
        """Mark an item resolved. Requires at least one piece of
        supporting evidence — a resolution can never be a bare
        assertion, exactly like BeliefSystem.form_belief(). Writes a
        final entry superseding the current one."""

        resolution = str(resolution).strip()

        if not resolution:
            raise ValueError(f"{self.RESOLUTION_LABEL} cannot be empty.")

        evidence = list(evidence or [])

        if not evidence:
            raise ValueError(
                f"A {self.ITEM_LABEL.lower()} cannot be resolved "
                "without at least one piece of supporting evidence."
            )

        current = self._get(entry_id)

        if current is None:
            raise ValueError(
                f"No {self.ITEM_LABEL.lower()} matches the supplied id."
            )

        status = self.status_of(current)

        if status != "open":
            raise ValueError(
                f"Cannot resolve a {status} {self.ITEM_LABEL.lower()}."
            )

        parsed = self._parse_content(current["content"])
        combined_evidence = list(parsed["evidence"]) + evidence

        content = self._format_content(
            statement=parsed["statement"],
            criteria=parsed["criteria"],
            budget=parsed["budget"],
            attempts=parsed["attempts"],
            predecessor=entry_id,
            resolution=resolution,
            evidence=combined_evidence,
            progress=parsed["progress"],
        )

        related = self._evidence_ids(combined_evidence)
        if entry_id not in related:
            related.append(entry_id)

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=current.get("source", "aion"),
            importance=current["importance"],
            tags=current.get("tags", []),
            related=related,
        )

        self.memory.add_tags(self.category, entry_id, ["superseded"])
        self.memory.add_tags(self.category, saved["id"], ["resolved"])

        return saved

    # ---------------------------------------------------------
    # ABANDON
    # ---------------------------------------------------------

    def abandon_item(self, entry_id, reason):
        """Abandon an item with no replacement. Tags it "abandoned"
        and logs a companion lessons entry recording why."""

        reason = str(reason).strip()

        if not reason:
            raise ValueError(
                f"A reason is required to abandon a "
                f"{self.ITEM_LABEL.lower()}."
            )

        current = self._get(entry_id)

        if current is None:
            raise ValueError(
                f"No {self.ITEM_LABEL.lower()} matches the supplied id."
            )

        status = self.status_of(current)

        if status != "open":
            raise ValueError(
                f"Cannot abandon a {status} {self.ITEM_LABEL.lower()}."
            )

        updated = self.memory.add_tags(
            self.category, entry_id, ["abandoned"]
        )

        self.memory.remember(
            category="lessons",
            content=(
                f"Abandoned {self.ITEM_LABEL.lower()} '{entry_id}': "
                f"{reason}"
            ),
            memory_type="lesson",
            source=f"{self.MEMORY_TYPE}-abandonment",
            importance=3,
            related=[entry_id],
        )

        return updated

    # ---------------------------------------------------------
    # QUERY
    # ---------------------------------------------------------

    def open_items(self, topic: str = None, limit: int = None):
        """Return currently open items (not superseded, resolved, or
        abandoned), highest priority first, then most recent."""

        results = []

        for entry in self.memory.all(self.category):

            if entry["type"] != self.MEMORY_TYPE:
                continue

            if self.status_of(entry) != "open":
                continue

            if topic is not None:
                entry_tags = [
                    tag.lower() for tag in entry.get("tags", [])
                ]
                if topic.strip().lower() not in entry_tags:
                    continue

            parsed = self._parse_content(entry["content"])
            results.append({
                **entry,
                **parsed,
                "budget_exhausted": (
                    parsed["attempts"] >= parsed["budget"]
                ),
            })

        results.sort(
            key=lambda entry: (entry["importance"], entry["timestamp"]),
            reverse=True,
        )

        if limit is not None:
            results = results[:limit]

        return results

    def history(self, entry_id: str):
        """Return the full history of one item, oldest first, by
        walking Predecessor links back from entry_id. Never filtered
        by status — superseded/resolved/abandoned states all stay
        visible."""

        by_id = {
            entry["id"]: entry
            for entry in self.memory.all(self.category)
            if entry["type"] == self.MEMORY_TYPE
        }

        if entry_id not in by_id:
            raise ValueError(
                f"No {self.ITEM_LABEL.lower()} matches the supplied id."
            )

        chain = []
        seen = set()
        current = by_id.get(entry_id)

        while current is not None and current["id"] not in seen:
            seen.add(current["id"])
            parsed = self._parse_content(current["content"])
            chain.append({**current, **parsed})

            predecessor_id = parsed.get("predecessor")
            current = by_id.get(predecessor_id) if predecessor_id else None

        chain.reverse()

        return chain

    def status_of(self, entry):
        """Classify an item entry as "open", "superseded", "resolved",
        or "abandoned", from its tags alone."""

        tags = [tag.lower() for tag in entry.get("tags", [])]

        if "abandoned" in tags:
            return "abandoned"

        if "resolved" in tags:
            return "resolved"

        if "superseded" in tags:
            return "superseded"

        return "open"

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _get(self, entry_id):
        for entry in self.memory.all(self.category):
            if entry["id"] == entry_id:
                return entry
        return None

    @staticmethod
    def _evidence_ids(evidence):
        ids = []

        for item in evidence:
            if isinstance(item, dict) and item.get("id"):
                entry_id = str(item["id"]).strip()
                if entry_id and entry_id not in ids:
                    ids.append(entry_id)

        return ids

    @classmethod
    def _format_evidence_line(cls, item):
        if isinstance(item, dict):
            description = str(item.get("description", "")).strip()
            entry_id = item.get("id")

            if entry_id:
                return f"- {description} (id: {entry_id})"

            return f"- {description}"

        return f"- {str(item).strip()}"

    def _format_content(
        self,
        statement,
        criteria,
        budget,
        attempts,
        predecessor,
        resolution,
        evidence,
        progress,
    ):
        lines = [
            f"{self.ITEM_LABEL}: {statement}",
            f"Criteria: {criteria}",
            f"Budget: {budget}",
            f"Attempts: {attempts}",
            f"Predecessor: {predecessor or 'none'}",
            f"{self.RESOLUTION_LABEL}: {resolution or 'none'}",
            "",
            "Evidence:",
        ]

        evidence_lines = [
            self._format_evidence_line(item) for item in evidence
        ] or ["- None"]
        lines.extend(evidence_lines)

        lines.append("")
        lines.append("Progress:")

        progress_lines = [f"- {note}" for note in progress] or ["- None"]
        lines.extend(progress_lines)

        return "\n".join(lines)

    def _parse_content(self, content):
        fields = {
            "statement": "",
            "criteria": "",
            "budget": 0,
            "attempts": 0,
            "predecessor": None,
            "resolution": None,
            "evidence": [],
            "progress": [],
        }

        current_section = None
        item_prefix = f"{self.ITEM_LABEL}:"
        resolution_prefix = f"{self.RESOLUTION_LABEL}:"

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith(item_prefix):
                fields["statement"] = line[len(item_prefix):].strip()
                current_section = None

            elif line.startswith("Criteria:"):
                fields["criteria"] = line[len("Criteria:"):].strip()
                current_section = None

            elif line.startswith("Budget:"):
                try:
                    fields["budget"] = int(
                        line[len("Budget:"):].strip()
                    )
                except ValueError:
                    fields["budget"] = 0
                current_section = None

            elif line.startswith("Attempts:"):
                try:
                    fields["attempts"] = int(
                        line[len("Attempts:"):].strip()
                    )
                except ValueError:
                    fields["attempts"] = 0
                current_section = None

            elif line.startswith("Predecessor:"):
                value = line[len("Predecessor:"):].strip()
                fields["predecessor"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line.startswith(resolution_prefix):
                value = line[len(resolution_prefix):].strip()
                fields["resolution"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line == "Evidence:":
                current_section = "evidence"

            elif line == "Progress:":
                current_section = "progress"

            elif current_section == "evidence" and line.startswith("- "):
                raw_item = line[2:].strip()

                if raw_item == "None":
                    continue

                match = self._EVIDENCE_ID_PATTERN.match(raw_item)

                if match:
                    fields["evidence"].append({
                        "description": match.group(1).strip(),
                        "id": match.group(2).strip(),
                    })
                else:
                    fields["evidence"].append(
                        {"description": raw_item, "id": None}
                    )

            elif current_section == "progress" and line.startswith("- "):
                raw_item = line[2:].strip()

                if raw_item != "None":
                    fields["progress"].append(raw_item)

        return fields
