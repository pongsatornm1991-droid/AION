"""Controlled belief mutation for AION.

Phase 6A.2A enables FORM and Phase 6A.3 enables SUPPORT:

    FORM
    SUPPORT

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
- SUPPORT may revise one active belief with new qualified evidence
- SUPPORT never changes the existing statement or lowers confidence
- replayed SUPPORT evidence is suppressed
- CONTRADICT / MIXED remain disabled
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

    def _active_belief_by_id(
        self,
        belief_id,
    ):
        target = str(
            belief_id or ""
        ).strip()

        if not target:
            return None

        for belief in (
            self.beliefs
            .active_beliefs()
        ):
            if str(
                belief.get("id") or ""
            ).strip() == target:
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

    def _validate_support(
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

        if proposal.get("stage") != "proposed":
            return (
                False,
                "Only a validated proposed belief action may mutate memory.",
                None,
            )

        if proposal.get("action") != "review_existing":
            return (
                False,
                "SUPPORT requires action='review_existing'.",
                None,
            )

        if proposal.get("relation") != "support":
            return (
                False,
                "Phase 6A.3 enables SUPPORT only for existing beliefs.",
                None,
            )

        target_id = str(
            proposal.get("related_belief_id") or ""
        ).strip()

        if not target_id:
            return (
                False,
                "SUPPORT must target an existing active belief.",
                None,
            )

        target_belief = self._active_belief_by_id(
            target_id
        )

        if target_belief is None:
            return (
                False,
                "SUPPORT target is missing or is no longer active.",
                None,
            )

        candidate_statement = self._normalize_text(
            proposal.get("candidate_statement")
        )
        existing_statement = self._normalize_text(
            target_belief.get("statement")
        )

        if not candidate_statement:
            return (
                False,
                "SUPPORT requires the existing belief statement.",
                None,
            )

        if (
            self._normalized_statement(candidate_statement)
            != self._normalized_statement(existing_statement)
        ):
            return (
                False,
                "SUPPORT may not change the target belief statement.",
                None,
            )

        confidence = proposal.get(
            "proposed_confidence"
        )

        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, Real)
        ):
            return (
                False,
                "SUPPORT requires numeric confidence.",
                None,
            )

        confidence = float(confidence)

        if not 0.0 <= confidence <= 1.0:
            return (
                False,
                "SUPPORT confidence must be between 0.0 and 1.0.",
                None,
            )

        current_confidence = float(
            target_belief.get("confidence", 0.0)
        )

        if confidence < current_confidence:
            return (
                False,
                "SUPPORT may not lower belief confidence.",
                None,
            )

        rationale = self._normalize_text(
            proposal.get("reason")
        )

        if not rationale:
            return (
                False,
                "SUPPORT requires an explicit rationale.",
                None,
            )

        qualified_map = self._qualified_evidence_map(
            qualified_evidence
        )

        if not qualified_map:
            return (
                False,
                "No qualified persisted evidence is available.",
                None,
            )

        proposal_ids = proposal.get("evidence_ids")

        if not isinstance(proposal_ids, list) or not proposal_ids:
            return (
                False,
                "SUPPORT requires persisted evidence IDs.",
                None,
            )

        cleaned_ids = []

        for value in proposal_ids:
            evidence_id = str(value or "").strip()

            if not evidence_id:
                return (
                    False,
                    "SUPPORT contains an empty evidence ID.",
                    None,
                )

            if evidence_id not in qualified_map:
                return (
                    False,
                    (
                        "SUPPORT references evidence outside the "
                        "supplied qualified evidence set."
                    ),
                    None,
                )

            if evidence_id not in cleaned_ids:
                cleaned_ids.append(evidence_id)

        existing_evidence_ids = {
            str(item.get("id") or "").strip()
            for item in target_belief.get("evidence", [])
            if isinstance(item, dict) and item.get("id")
        }
        new_evidence_ids = [
            evidence_id
            for evidence_id in cleaned_ids
            if evidence_id not in existing_evidence_ids
        ]

        return (
            True,
            None,
            {
                "statement": existing_statement,
                "confidence": confidence,
                "current_confidence": current_confidence,
                "rationale": rationale,
                "evidence_ids": cleaned_ids,
                "new_evidence_ids": new_evidence_ids,
                "qualified_map": qualified_map,
                "target_id": target_id,
                "target_belief": target_belief,
            },
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

    def _write_support_audit(
        self,
        belief_entry,
        validated,
    ):
        belief_id = str(
            belief_entry.get("id") or ""
        ).strip()
        predecessor_id = validated["target_id"]
        evidence_ids = validated["new_evidence_ids"]
        evidence_text = ", ".join(evidence_ids)

        content = (
            "Action: SUPPORT\n"
            f"Belief ID: {belief_id}\n"
            f"Predecessor ID: {predecessor_id}\n"
            f"Statement: {validated['statement']}\n"
            f"Previous Confidence: {validated['current_confidence']:.6f}\n"
            f"Confidence: {validated['confidence']:.6f}\n"
            f"Reason: {validated['rationale']}\n"
            f"Evidence IDs: {evidence_text}"
        )

        related = [
            value
            for value in (
                belief_id,
                predecessor_id,
                *evidence_ids,
            )
            if value
        ]

        return self.memory.remember(
            category=self.AUDIT_CATEGORY,
            content=content,
            memory_type="observation",
            source="belief-mutation",
            importance=3,
            tags=[
                "belief-mutation",
                "phase6a3",
                "support",
            ],
            related=related,
        )

    def _apply_support(
        self,
        proposal,
        qualified_evidence,
    ):
        valid, validation_reason, validated = (
            self._validate_support(
                proposal,
                qualified_evidence,
            )
        )

        if not valid:
            return self._no_change(
                stage="mutation-blocked",
                reason=validation_reason,
                proposal=proposal,
            )

        if not validated["new_evidence_ids"]:
            return {
                "stage": "duplicate-suppressed",
                "applied": False,
                "action": "no_change",
                "relation": "support",
                "belief_entry": validated["target_belief"],
                "audit_entry": None,
                "reason": (
                    "All SUPPORT evidence is already present in the "
                    "active belief lineage."
                ),
                "evidence_ids": [],
            }

        belief_evidence = self._evidence_for_belief(
            validated["new_evidence_ids"],
            validated["qualified_map"],
        )

        try:
            belief_entry = self.beliefs.revise_belief(
                entry_id=validated["target_id"],
                reason=validated["rationale"],
                new_confidence=validated["confidence"],
                additional_evidence=belief_evidence,
            )
        except Exception as exc:
            return {
                "stage": "mutation-error",
                "applied": False,
                "action": "no_change",
                "relation": "support",
                "belief_entry": None,
                "audit_entry": None,
                "reason": "Belief SUPPORT revision failed safely.",
                "error": f"{type(exc).__name__}: {exc}",
            }

        try:
            audit_entry = self._write_support_audit(
                belief_entry,
                validated,
            )
        except Exception as exc:
            return {
                "stage": "applied-with-audit-error",
                "applied": True,
                "action": "support",
                "relation": "support",
                "belief_entry": belief_entry,
                "audit_entry": None,
                "reason": (
                    "Belief was revised by SUPPORT, but the companion "
                    "mutation audit could not be persisted."
                ),
                "error": f"{type(exc).__name__}: {exc}",
            }

        return {
            "stage": "mutation-applied",
            "applied": True,
            "action": "support",
            "relation": "support",
            "belief_entry": belief_entry,
            "audit_entry": audit_entry,
            "reason": validated["rationale"],
            "evidence_ids": list(validated["new_evidence_ids"]),
            "predecessor_id": validated["target_id"],
        }

    def apply(
        self,
        proposal,
        qualified_evidence,
    ):
        """Apply one controlled mutation.

        Phase 6A.2A authorizes FORM. Phase 6A.3 authorizes SUPPORT.
        """

        if isinstance(proposal, dict) and (
            proposal.get("action") == "review_existing"
            or proposal.get("relation") == "support"
        ):
            return self._apply_support(
                proposal,
                qualified_evidence,
            )

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
    """Fault-isolated entry point for controlled learning mutations."""

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
