"""Controlled belief mutation for AION.

Phase 6A.2A enables one mutation only:

    FORM

All other belief relations remain read-only.

The mutation layer does not trust the provider proposal merely
because Phase 6A.1 validated it. It re-checks the fields required
to perform a persistent belief write.

Safety properties:

- no qualified evidence -> no mutation
- provider synthesis is never treated as evidence
- proposal evidence IDs must come from supplied qualified evidence
- FORM may not target an existing belief
- exact replayed statements are suppressed
- SUPPORT / CONTRADICT / MIXED remain disabled
- RETRACT remains disabled
- beliefs are created only through BeliefSystem
- mutation rationale is stored separately from factual evidence
- unexpected mutation failures are fault-isolated
"""

from numbers import Real

from brain.beliefs import BeliefSystem


class ControlledBeliefMutator:
    """Apply strictly bounded belief mutations."""

    AUDIT_CATEGORY = "belief_mutations"

    FORM_SOURCE = (
        "external-learning-belief-form"
    )

    FORM_TAGS = (
        "external-learning",
        "evidence-grounded",
        "phase6a2a",
    )

    def __init__(
        self,
        memory,
    ):
        self.memory = memory
        self.beliefs = BeliefSystem(
            memory
        )

    @staticmethod
    def _normalize_text(
        value,
    ):
        return " ".join(
            str(
                value or ""
            ).strip().split()
        )

    @classmethod
    def _normalized_statement(
        cls,
        value,
    ):
        return (
            cls._normalize_text(
                value
            )
            .casefold()
        )

    @staticmethod
    def _qualified_evidence_map(
        evidence,
    ):
        records = {}

        if not isinstance(
            evidence,
            list,
        ):
            return records

        for item in evidence:
            if not isinstance(
                item,
                dict,
            ):
                continue

            evidence_id = str(
                item.get(
                    "memory_id"
                )
                or item.get(
                    "id"
                )
                or ""
            ).strip()

            if not evidence_id:
                continue

            records[
                evidence_id
            ] = item

        return records

    @classmethod
    def _evidence_for_belief(
        cls,
        proposal_evidence_ids,
        qualified_map,
    ):
        result = []

        for evidence_id in (
            proposal_evidence_ids
        ):
            record = (
                qualified_map[
                    evidence_id
                ]
            )

            title = (
                cls._normalize_text(
                    record.get(
                        "title"
                    )
                )
                or "Qualified evidence"
            )

            url = cls._normalize_text(
                record.get(
                    "url"
                )
            )

            if url:
                description = (
                    f"{title} ({url})"
                )
            else:
                description = title

            result.append({
                "id": evidence_id,
                "description": description,
            })

        return result

    def _exact_active_duplicate(
        self,
        statement,
    ):
        target = (
            self._normalized_statement(
                statement
            )
        )

        if not target:
            return None

        for belief in (
            self.beliefs
            .active_beliefs()
        ):
            existing = (
                self
                ._normalized_statement(
                    belief.get(
                        "statement"
                    )
                )
            )

            if (
                existing
                and existing == target
            ):
                return belief

        return None

    @staticmethod
    def _no_change(
        stage,
        reason,
        proposal=None,
    ):
        relation = None
        action = "no_change"

        if isinstance(
            proposal,
            dict,
        ):
            relation = proposal.get(
                "relation"
            )

        return {
            "stage": stage,
            "applied": False,
            "action": action,
            "relation": relation,
            "belief_entry": None,
            "audit_entry": None,
            "reason": reason,
        }

    def _validate_form(
        self,
        proposal,
        qualified_evidence,
    ):
        if not isinstance(
            proposal,
            dict,
        ):
            return (
                False,
                "Belief proposal is missing or invalid.",
                None,
            )

        if (
            proposal.get("stage")
            != "proposed"
        ):
            return (
                False,
                "Only a validated proposed belief action may mutate memory.",
                None,
            )

        if (
            proposal.get("action")
            != "form"
        ):
            return (
                False,
                "Phase 6A.2A enables FORM only.",
                None,
            )

        if (
            proposal.get("relation")
            != "form"
        ):
            return (
                False,
                "FORM action requires relation='form'.",
                None,
            )

        if (
            proposal.get(
                "related_belief_id"
            )
            is not None
        ):
            return (
                False,
                "FORM may not target an existing belief.",
                None,
            )

        statement = (
            self._normalize_text(
                proposal.get(
                    "candidate_statement"
                )
            )
        )

        if not statement:
            return (
                False,
                "FORM requires a non-empty candidate statement.",
                None,
            )

        confidence = proposal.get(
            "proposed_confidence"
        )

        if (
            isinstance(
                confidence,
                bool,
            )
            or not isinstance(
                confidence,
                Real,
            )
        ):
            return (
                False,
                "FORM requires numeric confidence.",
                None,
            )

        confidence = float(
            confidence
        )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):
            return (
                False,
                "FORM confidence must be between 0.0 and 1.0.",
                None,
            )

        rationale = (
            self._normalize_text(
                proposal.get(
                    "reason"
                )
            )
        )

        if not rationale:
            return (
                False,
                "FORM requires an explicit rationale.",
                None,
            )

        qualified_map = (
            self
            ._qualified_evidence_map(
                qualified_evidence
            )
        )

        if not qualified_map:
            return (
                False,
                "No qualified persisted evidence is available.",
                None,
            )

        proposal_ids = proposal.get(
            "evidence_ids"
        )

        if (
            not isinstance(
                proposal_ids,
                list,
            )
            or not proposal_ids
        ):
            return (
                False,
                "FORM requires persisted evidence IDs.",
                None,
            )

        cleaned_ids = []

        for value in proposal_ids:
            evidence_id = str(
                value or ""
            ).strip()

            if not evidence_id:
                return (
                    False,
                    "FORM contains an empty evidence ID.",
                    None,
                )

            if (
                evidence_id
                not in qualified_map
            ):
                return (
                    False,
                    (
                        "FORM references evidence "
                        "outside the supplied qualified "
                        "evidence set."
                    ),
                    None,
                )

            if (
                evidence_id
                not in cleaned_ids
            ):
                cleaned_ids.append(
                    evidence_id
                )

        if not cleaned_ids:
            return (
                False,
                "FORM requires at least one qualified evidence ID.",
                None,
            )

        validated = {
            "statement": statement,
            "confidence": confidence,
            "rationale": rationale,
            "evidence_ids": (
                cleaned_ids
            ),
            "qualified_map": (
                qualified_map
            ),
        }

        return (
            True,
            None,
            validated,
        )

    def _write_audit(
        self,
        belief_entry,
        validated,
    ):
        belief_id = str(
            belief_entry.get(
                "id"
            )
            or ""
        ).strip()

        evidence_ids = (
            validated[
                "evidence_ids"
            ]
        )

        evidence_text = ", ".join(
            evidence_ids
        )

        content = (
            "Action: FORM\n"
            f"Belief ID: {belief_id}\n"
            f"Statement: {validated['statement']}\n"
            f"Confidence: {validated['confidence']:.6f}\n"
            f"Reason: {validated['rationale']}\n"
            f"Evidence IDs: {evidence_text}"
        )

        related = []

        if belief_id:
            related.append(
                belief_id
            )

        related.extend(
            evidence_ids
        )

        return self.memory.remember(
            category=(
                self.AUDIT_CATEGORY
            ),
            content=content,
            memory_type="observation",
            source="belief-mutation",
            importance=3,
            tags=[
                "belief-mutation",
                "phase6a2a",
                "form",
            ],
            related=related,
        )

    def apply(
        self,
        proposal,
        qualified_evidence,
    ):
        """Apply one controlled mutation.

        Phase 6A.2A authorizes FORM only.
        """

        (
            valid,
            validation_reason,
            validated,
        ) = self._validate_form(
            proposal,
            qualified_evidence,
        )

        if not valid:
            return self._no_change(
                stage="mutation-blocked",
                reason=validation_reason,
                proposal=proposal,
            )

        duplicate = (
            self
            ._exact_active_duplicate(
                validated[
                    "statement"
                ]
            )
        )

        if duplicate is not None:
            return {
                "stage": (
                    "duplicate-suppressed"
                ),
                "applied": False,
                "action": "no_change",
                "relation": "form",
                "belief_entry": duplicate,
                "audit_entry": None,
                "reason": (
                    "An exact active belief "
                    "with this statement already exists."
                ),
            }

        belief_evidence = (
            self
            ._evidence_for_belief(
                validated[
                    "evidence_ids"
                ],
                validated[
                    "qualified_map"
                ],
            )
        )

        try:
            belief_entry = (
                self.beliefs
                .form_belief(
                    statement=(
                        validated[
                            "statement"
                        ]
                    ),
                    confidence=(
                        validated[
                            "confidence"
                        ]
                    ),
                    evidence=(
                        belief_evidence
                    ),
                    tags=list(
                        self.FORM_TAGS
                    ),
                    source=(
                        self.FORM_SOURCE
                    ),
                )
            )

        except Exception as exc:
            return {
                "stage": (
                    "mutation-error"
                ),
                "applied": False,
                "action": "no_change",
                "relation": "form",
                "belief_entry": None,
                "audit_entry": None,
                "reason": (
                    "Belief FORM failed safely."
                ),
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

        try:
            audit_entry = (
                self._write_audit(
                    belief_entry,
                    validated,
                )
            )

        except Exception as exc:
            return {
                "stage": (
                    "applied-with-audit-error"
                ),
                "applied": True,
                "action": "form",
                "relation": "form",
                "belief_entry": (
                    belief_entry
                ),
                "audit_entry": None,
                "reason": (
                    "Belief was formed, but the "
                    "companion mutation audit "
                    "could not be persisted."
                ),
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

        return {
            "stage": "mutation-applied",
            "applied": True,
            "action": "form",
            "relation": "form",
            "belief_entry": (
                belief_entry
            ),
            "audit_entry": (
                audit_entry
            ),
            "reason": (
                validated[
                    "rationale"
                ]
            ),
            "evidence_ids": list(
                validated[
                    "evidence_ids"
                ]
            ),
        }


def safely_apply_belief_mutation(
    memory,
    proposal,
    qualified_evidence,
):
    """Fault-isolated entry point for future learning wiring."""

    try:
        return (
            ControlledBeliefMutator(
                memory
            ).apply(
                proposal=proposal,
                qualified_evidence=(
                    qualified_evidence
                ),
            )
        )

    except Exception as exc:
        return {
            "stage": "mutation-error",
            "applied": False,
            "action": "no_change",
            "relation": None,
            "belief_entry": None,
            "audit_entry": None,
            "reason": (
                "Controlled belief mutation "
                "failed safely."
            ),
            "error": (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        }
