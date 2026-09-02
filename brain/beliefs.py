import re
from datetime import datetime, timedelta


class BeliefSystem:
    """AION's explicit belief store: claims held with confidence,
    evidence, revision history, and an expiration date.

    This is the "self-model owns its own brain" component in code
    form: a belief can never be created from bare AI output.
    form_belief() refuses to save anything with no supporting
    evidence at all, so whatever calls it (a CLI operator, Thinker,
    a future reflection step) must supply concrete grounds itself —
    a sentence a provider generated is never, on its own, enough to
    become a belief.

    Revising a belief never edits history in place. It writes a new
    belief entry linked back to its predecessor (the "Predecessor:"
    field, mirrored in the memory engine's `related` metadata) and
    tags the old entry "superseded" — the full lineage stays on disk
    and auditable via history(). Beliefs are never deleted: retracting
    one only tags it "retracted" and records why as a companion
    lesson entry.
    """

    CATEGORY = "beliefs"
    # 2026-09-02, at the user's explicit request: beliefs never
    # expire by default. A belief record is already permanent on
    # disk either way (see the class docstring -- "Beliefs are
    # never deleted"); this default controlled only whether a
    # belief silently stopped being "active" (and so stopped
    # informing future drafts via active_beliefs()) after 90 days
    # with no human or code ever revisiting it. Explicit callers
    # can still pass expires_in_days=<N> to form_belief()/
    # revise_belief() for a belief that genuinely should lapse on
    # its own (e.g. something time-bound); nothing expires by
    # default anymore.
    DEFAULT_EXPIRES_DAYS = None

    _EVIDENCE_ID_PATTERN = re.compile(r"^(.*?)\(id:\s*(.+?)\)\s*$")

    def __init__(self, memory, category=None):
        self.memory = memory
        self.category = category or self.CATEGORY

    # ---------------------------------------------------------
    # FORM
    # ---------------------------------------------------------

    def form_belief(
        self,
        statement: str,
        confidence: float,
        evidence: list,
        tags: list = None,
        source: str = "aion",
        expires_in_days: int = None,
    ):
        """Save a new belief. Raises ValueError if no evidence is
        supplied — a belief cannot be formed on confidence alone."""

        statement = str(statement).strip()

        if not statement:
            raise ValueError("Belief statement cannot be empty.")

        self._validate_confidence(confidence)

        evidence = list(evidence or [])

        if not evidence:
            raise ValueError(
                "A belief cannot be formed without at least one piece "
                "of supporting evidence."
            )

        expires = self._expiry_date(
            self._validate_expires_in_days(expires_in_days)
        )

        content = self._format_belief_content(
            statement=statement,
            confidence=confidence,
            expires=expires,
            predecessor=None,
            evidence=evidence,
        )

        return self.memory.remember(
            category=self.category,
            content=content,
            memory_type="belief",
            source=source,
            importance=self._confidence_to_importance(confidence),
            tags=tags,
            related=self._evidence_ids(evidence),
        )

    # ---------------------------------------------------------
    # REVISE
    # ---------------------------------------------------------

    def revise_belief(
        self,
        entry_id: str,
        reason: str,
        new_statement: str = None,
        new_confidence: float = None,
        additional_evidence: list = None,
        expires_in_days: int = None,
    ):
        """Create a new belief entry superseding an existing one. The
        old entry is never edited or deleted — only tagged
        "superseded" and kept as part of the permanent lineage."""

        reason = str(reason).strip()

        if not reason:
            raise ValueError("A revision reason is required.")

        existing = self._get(entry_id)

        if existing is None:
            raise ValueError("No belief entry matches the supplied id.")

        status = self.status_of(existing)

        if status != "active":
            raise ValueError(
                f"Cannot revise a belief that is already {status}."
            )

        parsed = self._parse_belief_content(existing["content"])

        statement = (
            str(new_statement).strip()
            if new_statement is not None
            else parsed["statement"]
        )

        if new_confidence is not None:
            self._validate_confidence(new_confidence)
            confidence = new_confidence
        else:
            confidence = parsed["confidence"]

        combined_evidence = list(parsed["evidence"]) + list(
            additional_evidence or []
        )
        combined_evidence.append(
            {"description": f"Revision reason: {reason}"}
        )

        expires = self._expiry_date(
            self._validate_expires_in_days(expires_in_days)
        )

        content = self._format_belief_content(
            statement=statement,
            confidence=confidence,
            expires=expires,
            predecessor=entry_id,
            evidence=combined_evidence,
        )

        related = self._evidence_ids(combined_evidence)
        if entry_id not in related:
            related.append(entry_id)

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type="belief",
            source=existing.get("source", "aion"),
            importance=self._confidence_to_importance(confidence),
            tags=existing.get("tags", []),
            related=related,
        )

        self.memory.add_tags(self.category, entry_id, ["superseded"])

        return saved

    # ---------------------------------------------------------
    # RETRACT
    # ---------------------------------------------------------

    def retract_belief(self, entry_id: str, reason: str):
        """Mark a belief retracted, with no replacement. Use
        revise_belief() instead when a corrected belief should take
        its place."""

        reason = str(reason).strip()

        if not reason:
            raise ValueError("A retraction reason is required.")

        existing = self._get(entry_id)

        if existing is None:
            raise ValueError("No belief entry matches the supplied id.")

        status = self.status_of(existing)

        if status != "active":
            raise ValueError(
                f"Cannot retract a belief that is already {status}."
            )

        updated = self.memory.add_tags(
            self.category, entry_id, ["retracted"]
        )

        self.memory.remember(
            category="lessons",
            content=f"Retracted belief '{entry_id}': {reason}",
            memory_type="lesson",
            source="belief-retraction",
            importance=3,
            related=[entry_id],
        )

        return updated

    # ---------------------------------------------------------
    # QUERY
    # ---------------------------------------------------------

    def active_beliefs(self, topic: str = None, limit: int = None):
        """Return currently active beliefs (not superseded, retracted,
        or expired), most recent first."""

        results = []

        for entry in self.memory.all(self.category):

            if entry["type"] != "belief":
                continue

            if self.status_of(entry) != "active":
                continue

            if topic is not None:
                entry_tags = [
                    tag.lower() for tag in entry.get("tags", [])
                ]
                if topic.strip().lower() not in entry_tags:
                    continue

            parsed = self._parse_belief_content(entry["content"])
            results.append({**entry, **parsed})

        results.sort(key=lambda entry: entry["timestamp"], reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def history(self, entry_id: str):
        """Return the full revision lineage of a belief, oldest
        first, by walking Predecessor links back from entry_id.
        Includes superseded/retracted ancestors — history is never
        filtered by status."""

        by_id = {
            entry["id"]: entry
            for entry in self.memory.all(self.category)
            if entry["type"] == "belief"
        }

        if entry_id not in by_id:
            raise ValueError("No belief entry matches the supplied id.")

        chain = []
        seen = set()
        current = by_id.get(entry_id)

        while current is not None and current["id"] not in seen:
            seen.add(current["id"])
            parsed = self._parse_belief_content(current["content"])
            chain.append({**current, **parsed})

            predecessor_id = parsed.get("predecessor")
            current = by_id.get(predecessor_id) if predecessor_id else None

        chain.reverse()

        return chain

    def status_of(self, entry):
        """Classify a belief entry as "active", "superseded",
        "retracted", or "expired". Expiration is computed from the
        stored Expires date at read time, not a stored state
        transition."""

        tags = [tag.lower() for tag in entry.get("tags", [])]

        if "retracted" in tags:
            return "retracted"

        if "superseded" in tags:
            return "superseded"

        parsed = self._parse_belief_content(entry["content"])
        expires = parsed.get("expires")

        if expires:
            try:
                expiry_date = datetime.strptime(
                    expires, "%Y-%m-%d"
                ).date()
                if expiry_date < datetime.now().date():
                    return "expired"
            except ValueError:
                pass

        return "active"

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _get(self, entry_id):
        for entry in self.memory.all(self.category):
            if entry["id"] == entry_id:
                return entry
        return None

    @staticmethod
    def _validate_confidence(confidence):
        if not isinstance(confidence, (int, float)) or isinstance(
            confidence, bool
        ):
            raise TypeError(
                "Confidence must be a number between 0.0 and 1.0."
            )

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Confidence must be between 0.0 and 1.0."
            )

    @staticmethod
    def _validate_expires_in_days(expires_in_days):
        if expires_in_days is None:
            return BeliefSystem.DEFAULT_EXPIRES_DAYS

        if not isinstance(expires_in_days, int) or isinstance(
            expires_in_days, bool
        ):
            raise TypeError("expires_in_days must be an integer.")

        if expires_in_days < 0:
            raise ValueError("expires_in_days cannot be negative.")

        return expires_in_days

    @staticmethod
    def _confidence_to_importance(confidence):
        return max(1, min(5, 1 + round(confidence * 4)))

    @staticmethod
    def _expiry_date(expires_in_days):
        if not expires_in_days:
            return None

        return (
            datetime.now() + timedelta(days=expires_in_days)
        ).strftime("%Y-%m-%d")

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

    @classmethod
    def _format_belief_content(
        cls, statement, confidence, expires, predecessor, evidence
    ):
        lines = [
            f"Statement: {statement}",
            f"Confidence: {confidence:.2f}",
            f"Expires: {expires or 'none'}",
            f"Predecessor: {predecessor or 'none'}",
            "",
            "Evidence:",
        ]

        evidence_lines = [
            cls._format_evidence_line(item) for item in evidence
        ] or ["- None"]

        lines.extend(evidence_lines)

        return "\n".join(lines)

    @classmethod
    def _parse_belief_content(cls, content):
        fields = {
            "statement": "",
            "confidence": 0.0,
            "expires": None,
            "predecessor": None,
            "evidence": [],
        }

        current_section = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("Statement:"):
                fields["statement"] = line[len("Statement:"):].strip()
                current_section = None

            elif line.startswith("Confidence:"):
                try:
                    fields["confidence"] = float(
                        line[len("Confidence:"):].strip()
                    )
                except ValueError:
                    fields["confidence"] = 0.0
                current_section = None

            elif line.startswith("Expires:"):
                value = line[len("Expires:"):].strip()
                fields["expires"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line.startswith("Predecessor:"):
                value = line[len("Predecessor:"):].strip()
                fields["predecessor"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line == "Evidence:":
                current_section = "evidence"

            elif current_section == "evidence" and line.startswith("- "):
                raw_item = line[2:].strip()

                if raw_item == "None":
                    continue

                match = cls._EVIDENCE_ID_PATTERN.match(raw_item)

                if match:
                    fields["evidence"].append({
                        "description": match.group(1).strip(),
                        "id": match.group(2).strip(),
                    })
                else:
                    fields["evidence"].append(
                        {"description": raw_item, "id": None}
                    )

        return fields
