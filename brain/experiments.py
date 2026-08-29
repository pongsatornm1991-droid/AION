import re


class ExperimentEngine:
    """AION's predict -> observe -> conclude loop.

    This is the "Experiments and reflection" cycle from the roadmap
    made concrete: state a prediction with a confidence level before
    anything is known, record what was actually observed (always with
    evidence — an observation is itself a claim, and claims are never
    asserted for free anywhere in this codebase), and only then derive
    a lesson. Optionally, concluding an experiment can drive a real
    BeliefSystem revision, so a measured surprise actually changes
    what AION believes rather than just being noted and forgotten.

    Like BeliefSystem and BoundedItemTracker, nothing here is ever
    edited in place: each stage (observe, conclude) writes a brand-new
    entry linked back to its predecessor and tags the old one
    "superseded", so the full predict/observe/conclude trail stays on
    disk. Whether a prediction "matched" is never inferred by this
    class — the caller states it explicitly (`matched=True/False`),
    and a mismatch requires an explicit error description. Nothing is
    computed or judged here that this code cannot verify itself.
    """

    CATEGORY = "experiments"
    MEMORY_TYPE = "experiment"

    _EVIDENCE_ID_PATTERN = re.compile(r"^(.*?)\(id:\s*(.+?)\)\s*$")

    def __init__(self, memory, category=None):
        self.memory = memory
        self.category = category or self.CATEGORY

    # ---------------------------------------------------------
    # PREDICT
    # ---------------------------------------------------------

    def predict(
        self,
        prediction: str,
        confidence: float,
        tags: list = None,
        source: str = "aion",
    ):
        """Record a prediction before anything is observed. No
        evidence is required here — a prediction is a stated
        expectation, not a claim of fact; evidence is required at the
        observe() step instead, where a claim about reality is
        actually being made."""

        prediction = str(prediction).strip()

        if not prediction:
            raise ValueError("Prediction cannot be empty.")

        self._validate_confidence(confidence)

        content = self._format_content(
            prediction=prediction,
            confidence=confidence,
            predecessor=None,
            observed=None,
            matched=None,
            error=None,
            lesson=None,
            evidence=[],
        )

        return self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=source,
            importance=self._confidence_to_importance(confidence),
            tags=tags,
        )

    # ---------------------------------------------------------
    # OBSERVE
    # ---------------------------------------------------------

    def observe(
        self,
        entry_id: str,
        observed_result: str,
        matched: bool,
        evidence: list,
        error_description: str = None,
    ):
        """Record what was actually observed. Requires evidence — an
        observation is a claim, and claims need evidence throughout
        this codebase. If matched is False, error_description is
        required: a mismatch can never be logged without saying what
        the mismatch actually was."""

        current = self._get(entry_id)

        if current is None:
            raise ValueError("No experiment matches the supplied id.")

        status = self.status_of(current)

        if status != "predicted":
            raise ValueError(
                f"Cannot observe an experiment that is already {status}."
            )

        observed_result = str(observed_result).strip()

        if not observed_result:
            raise ValueError("Observed result cannot be empty.")

        evidence = list(evidence or [])

        if not evidence:
            raise ValueError(
                "An observation cannot be recorded without at least "
                "one piece of supporting evidence."
            )

        if not isinstance(matched, bool):
            raise TypeError("matched must be True or False.")

        error_description = (
            str(error_description).strip() if error_description else ""
        )

        if not matched and not error_description:
            raise ValueError(
                "A mismatched prediction requires an error_description "
                "explaining what the mismatch was."
            )

        parsed = self._parse_content(current["content"])

        content = self._format_content(
            prediction=parsed["prediction"],
            confidence=parsed["confidence"],
            predecessor=entry_id,
            observed=observed_result,
            matched=matched,
            error=error_description or None,
            lesson=None,
            evidence=evidence,
        )

        related = self._evidence_ids(evidence)
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

        return saved

    # ---------------------------------------------------------
    # CONCLUDE
    # ---------------------------------------------------------

    def conclude(
        self,
        entry_id: str,
        lesson: str,
        belief_system=None,
        belief_id: str = None,
        new_belief_confidence: float = None,
    ):
        """Derive a lesson from an observed experiment and log it to
        memory/lessons.md. Optionally drives a real BeliefSystem
        revision when belief_system and belief_id are both supplied,
        so a measured result can actually change what AION believes —
        never automatically, only when the caller explicitly asks for
        it and supplies the belief to revise."""

        current = self._get(entry_id)

        if current is None:
            raise ValueError("No experiment matches the supplied id.")

        status = self.status_of(current)

        if status != "observed":
            raise ValueError(
                f"Cannot conclude an experiment that is {status} "
                "(it must be observed first)."
            )

        lesson = str(lesson).strip()

        if not lesson:
            raise ValueError("Lesson cannot be empty.")

        parsed = self._parse_content(current["content"])

        content = self._format_content(
            prediction=parsed["prediction"],
            confidence=parsed["confidence"],
            predecessor=entry_id,
            observed=parsed["observed"],
            matched=parsed["matched"],
            error=parsed["error"],
            lesson=lesson,
            evidence=parsed["evidence"],
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

        self.memory.remember(
            category="lessons",
            content=(
                f"From experiment '{saved['id']}' "
                f"(predicted: {parsed['prediction']!r}, "
                f"matched: {parsed['matched']}): {lesson}"
            ),
            memory_type="lesson",
            source="experiment-conclusion",
            importance=current["importance"],
            related=[saved["id"]],
        )

        revised_belief = None

        if belief_system is not None and belief_id is not None:
            revised_belief = belief_system.revise_belief(
                entry_id=belief_id,
                reason=(
                    f"Experiment '{saved['id']}' concluded: {lesson}"
                ),
                new_confidence=new_belief_confidence,
                additional_evidence=[{
                    "id": saved["id"],
                    "description": (
                        f"Experiment observation: {parsed['observed']}"
                    ),
                }],
            )

        return {"experiment": saved, "revised_belief": revised_belief}

    # ---------------------------------------------------------
    # ABANDON
    # ---------------------------------------------------------

    def abandon(self, entry_id: str, reason: str):
        """Abandon an experiment before it is concluded (e.g. it
        became irrelevant, or could not be observed). Tags it
        "abandoned" and logs why as a companion lessons entry."""

        reason = str(reason).strip()

        if not reason:
            raise ValueError("A reason is required to abandon an experiment.")

        current = self._get(entry_id)

        if current is None:
            raise ValueError("No experiment matches the supplied id.")

        status = self.status_of(current)

        if status not in ("predicted", "observed"):
            raise ValueError(f"Cannot abandon an experiment that is {status}.")

        updated = self.memory.add_tags(
            self.category, entry_id, ["abandoned"]
        )

        self.memory.remember(
            category="lessons",
            content=f"Abandoned experiment '{entry_id}': {reason}",
            memory_type="lesson",
            source="experiment-abandonment",
            importance=3,
            related=[entry_id],
        )

        return updated

    # ---------------------------------------------------------
    # QUERY
    # ---------------------------------------------------------

    def status_of(self, entry):
        """Classify the latest entry in an experiment's chain as
        "predicted", "observed", "concluded", or "abandoned"."""

        tags = [tag.lower() for tag in entry.get("tags", [])]

        if "abandoned" in tags:
            return "abandoned"

        parsed = self._parse_content(entry["content"])

        if parsed["lesson"] is not None:
            return "concluded"

        if parsed["observed"] is not None:
            return "observed"

        return "predicted"

    def _latest_entries(self):
        """All non-superseded experiment entries (the current head of
        each predict/observe/conclude chain)."""

        results = []

        for entry in self.memory.all(self.category):
            if entry["type"] != self.MEMORY_TYPE:
                continue

            tags = [tag.lower() for tag in entry.get("tags", [])]
            if "superseded" in tags:
                continue

            results.append(entry)

        return results

    def pending_experiments(self, limit: int = None):
        """Experiments predicted but not yet observed."""

        results = [
            {**entry, **self._parse_content(entry["content"])}
            for entry in self._latest_entries()
            if self.status_of(entry) == "predicted"
        ]
        results.sort(key=lambda entry: entry["timestamp"], reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def awaiting_conclusion(self, limit: int = None):
        """Experiments observed but not yet concluded with a lesson."""

        results = [
            {**entry, **self._parse_content(entry["content"])}
            for entry in self._latest_entries()
            if self.status_of(entry) == "observed"
        ]
        results.sort(key=lambda entry: entry["timestamp"], reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def observed_experiments(self, limit: int = None):
        """Every experiment that has actually been observed at least
        once (matched is known), regardless of whether it has since
        been concluded or abandoned. This is the raw material for
        calibration analysis (Metacognition): predicted-but-never-
        observed experiments carry no signal, so they are excluded."""

        results = [
            {**entry, **self._parse_content(entry["content"])}
            for entry in self._latest_entries()
            if self._parse_content(entry["content"])["matched"] is not None
        ]
        results.sort(key=lambda entry: entry["timestamp"], reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def history(self, entry_id: str):
        """Full predict -> observe -> conclude chain for one
        experiment, oldest first. Never filtered by status."""

        by_id = {
            entry["id"]: entry
            for entry in self.memory.all(self.category)
            if entry["type"] == self.MEMORY_TYPE
        }

        if entry_id not in by_id:
            raise ValueError("No experiment matches the supplied id.")

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
            raise ValueError("Confidence must be between 0.0 and 1.0.")

    @staticmethod
    def _confidence_to_importance(confidence):
        return max(1, min(5, 1 + round(confidence * 4)))

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
    def _format_content(
        cls,
        prediction,
        confidence,
        predecessor,
        observed,
        matched,
        error,
        lesson,
        evidence,
    ):
        if matched is None:
            matched_text = "unknown"
        else:
            matched_text = "yes" if matched else "no"

        lines = [
            f"Prediction: {prediction}",
            f"Confidence: {confidence:.2f}",
            f"Predecessor: {predecessor or 'none'}",
            f"Observed: {observed or 'none'}",
            f"Matched: {matched_text}",
            f"Error: {error or 'none'}",
            f"Lesson: {lesson or 'none'}",
            "",
            "Evidence:",
        ]

        evidence_lines = [
            cls._format_evidence_line(item) for item in evidence
        ] or ["- None"]
        lines.extend(evidence_lines)

        return "\n".join(lines)

    @classmethod
    def _parse_content(cls, content):
        fields = {
            "prediction": "",
            "confidence": 0.0,
            "predecessor": None,
            "observed": None,
            "matched": None,
            "error": None,
            "lesson": None,
            "evidence": [],
        }

        current_section = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("Prediction:"):
                fields["prediction"] = line[len("Prediction:"):].strip()
                current_section = None

            elif line.startswith("Confidence:"):
                try:
                    fields["confidence"] = float(
                        line[len("Confidence:"):].strip()
                    )
                except ValueError:
                    fields["confidence"] = 0.0
                current_section = None

            elif line.startswith("Predecessor:"):
                value = line[len("Predecessor:"):].strip()
                fields["predecessor"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line.startswith("Observed:"):
                value = line[len("Observed:"):].strip()
                fields["observed"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line.startswith("Matched:"):
                value = line[len("Matched:"):].strip().lower()
                if value == "yes":
                    fields["matched"] = True
                elif value == "no":
                    fields["matched"] = False
                else:
                    fields["matched"] = None
                current_section = None

            elif line.startswith("Error:"):
                value = line[len("Error:"):].strip()
                fields["error"] = (
                    None if value.lower() == "none" else value
                )
                current_section = None

            elif line.startswith("Lesson:"):
                value = line[len("Lesson:"):].strip()
                fields["lesson"] = (
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
