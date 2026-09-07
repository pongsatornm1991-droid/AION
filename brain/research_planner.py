"""Autonomous evidence-source planning for AION.

The planner decides WHICH implemented source adapter is appropriate for
the evidence required by an open curiosity question.

Important distinction:

    SourceRegistry
        describes sources and evidence capabilities.

    ResearchAdapter
        grants the actual technical ability to retrieve from a source.

    AutonomousResearchPlanner
        chooses among currently available adapters.

A registry entry alone never grants network access.

The planner does not decide what AION should believe and does not decide
whether completion criteria are satisfied. Those responsibilities remain
with the evidence and completion-criteria layers.
"""


class AutonomousResearchPlanner:
    """Choose an appropriate evidence source for a research requirement."""

    TIER_SCORES = {
        "A": 30,
        "B": 20,
        "C": 10,
    }

    def __init__(self, source_registry):
        self.source_registry = source_registry

    @staticmethod
    def _clean_capabilities(source):
        return {
            str(item).strip()
            for item in source.get("capabilities", [])
            if str(item).strip()
        }

    @classmethod
    def _tier_score(cls, source):
        tier = str(
            source.get("tier", "")
        ).strip().upper()

        return cls.TIER_SCORES.get(
            tier,
            0,
        )

    @staticmethod
    def _source_id(source):
        return str(
            source.get("id", "")
        ).strip()

    @staticmethod
    def _existing_source_kinds(existing_evidence):
        return {
            str(
                item.get(
                    "source_kind",
                    "",
                )
            ).strip()
            for item in (existing_evidence or [])
            if str(
                item.get(
                    "source_kind",
                    "",
                )
            ).strip()
        }

    def _enabled_sources(self):
        enabled_fn = getattr(
            self.source_registry,
            "enabled_sources",
            None,
        )

        if not callable(enabled_fn):
            return []

        try:
            sources = enabled_fn()
        except Exception:
            return []

        return [
            source
            for source in sources
            if isinstance(source, dict)
            and self._source_id(source)
        ]

    def plan(
        self,
        requirement_report,
        available_adapter_ids,
        existing_evidence=None,
    ):
        """Create a bounded research plan.

        Parameters
        ----------
        requirement_report:
            Output from EvidenceRequirementAnalyzer.

        available_adapter_ids:
            IDs of adapters that are actually implemented and usable.

        existing_evidence:
            Previously persisted research evidence for the same root
            curiosity question.

        Returns
        -------
        dict
            Machine-readable research plan.
        """

        requirement_report = dict(
            requirement_report or {}
        )

        required_types = [
            str(item).strip()
            for item in requirement_report.get(
                "evidence_types",
                [],
            )
            if str(item).strip()
        ]

        if not required_types:
            required_types = [
                "general_external"
            ]

        required_count = requirement_report.get(
            "required_count"
        )

        available_adapter_ids = {
            str(item).strip()
            for item in (available_adapter_ids or [])
            if str(item).strip()
        }

        existing_evidence = list(
            existing_evidence or []
        )

        existing_source_kinds = (
            self._existing_source_kinds(
                existing_evidence
            )
        )

        candidates = []

        for source in self._enabled_sources():
            source_id = self._source_id(
                source
            )

            if source_id not in available_adapter_ids:
                continue

            capabilities = (
                self._clean_capabilities(
                    source
                )
            )

            matched_types = [
                evidence_type
                for evidence_type in required_types
                if evidence_type in capabilities
            ]

            if not matched_types:
                continue

            score = self._tier_score(
                source
            )

            # Prefer a different source when multiple valid adapters
            # exist and evidence from one source kind already exists.
            if source_id not in existing_source_kinds:
                score += 5

            # Prefer sources matching more of the explicit evidence
            # requirements.
            score += (
                len(matched_types) * 10
            )

            candidates.append({
                "source_id": source_id,
                "name": str(
                    source.get(
                        "name",
                        source_id,
                    )
                ).strip(),
                "tier": str(
                    source.get(
                        "tier",
                        "",
                    )
                ).strip(),
                "capabilities": sorted(
                    capabilities
                ),
                "matched_evidence_types": (
                    matched_types
                ),
                "score": score,
            })

        candidates.sort(
            key=lambda item: (
                -item["score"],
                item["source_id"],
            )
        )

        if not candidates:
            return {
                "status": "capability-needed",
                "source_id": None,
                "target_evidence_type": (
                    required_types[0]
                    if required_types
                    else "general_external"
                ),
                "required_evidence_types": (
                    required_types
                ),
                "required_count": required_count,
                "existing_evidence_count": len(
                    existing_evidence
                ),
                "candidates": [],
                "reason": (
                    "No currently implemented and enabled "
                    "research adapter can retrieve the "
                    "required evidence type."
                ),
            }

        chosen = candidates[0]

        target_type = (
            chosen[
                "matched_evidence_types"
            ][0]
        )

        missing_count = None

        if isinstance(
            required_count,
            int,
        ):
            missing_count = max(
                required_count
                - len(existing_evidence),
                0,
            )

        return {
            "status": "ready",
            "source_id": (
                chosen["source_id"]
            ),
            "source_name": (
                chosen["name"]
            ),
            "target_evidence_type": (
                target_type
            ),
            "required_evidence_types": (
                required_types
            ),
            "required_count": required_count,
            "existing_evidence_count": len(
                existing_evidence
            ),
            "missing_evidence_count": (
                missing_count
            ),
            "candidates": candidates,
            "reason": (
                "Selected the highest-ranked enabled "
                "adapter whose declared capabilities "
                "match the question's evidence "
                "requirements."
            ),
        }