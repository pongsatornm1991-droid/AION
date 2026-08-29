from datetime import datetime


class MemoryConsolidator:
    """Summarize old, low-importance episodic memories into semantic
    knowledge.

    This routine deliberately keeps every decision that matters inside
    AION's own code, never delegated to the AI provider:

    - WHAT counts as a consolidation candidate (age, importance,
      whether it was already consolidated) is decided here, in plain
      Python, before any provider is touched.
    - WHETHER a drafted summary is safe/high-quality enough to keep is
      decided by OutputEvaluator (the same safety gate used for
      reflections), not by the provider's own opinion of its output.
    - The provider is only ever asked to draft a summary of content
      AION has already selected and can already see in full; it is
      never trusted to decide on its own what is true or what belongs
      in memory.

    A rejected or too-small batch always leaves the source entries
    untouched — consolidation only ever removes entries from the live
    category once a safe summary has actually been saved, so nothing
    is lost silently.
    """

    def __init__(
        self,
        memory,
        provider,
        evaluator=None,
        min_group_size=3,
        max_importance=2,
        min_age_days=30,
        min_claim_safety=5,
    ):
        if evaluator is None:
            from brain.evaluator import OutputEvaluator
            evaluator = OutputEvaluator()

        self.memory = memory
        self.provider = provider
        self.evaluator = evaluator
        self.min_group_size = min_group_size
        self.max_importance = max_importance
        self.min_age_days = min_age_days
        # OutputEvaluator's overall_score also grades reflection-
        # specific structure (self-knowledge/uncertainty/future-
        # understanding/learning-objective sections) that a short
        # memory summary never has and shouldn't be judged against.
        # Consolidation only cares whether the summary itself makes
        # any unsafe/unsupported claim, so it gates on the
        # claim_safety sub-score alone (5 = no violation detected,
        # 0 = at least one).
        self.min_claim_safety = min_claim_safety

    # ---------------------------------------------------------
    # SELECTION (pure code, no AI call)
    # ---------------------------------------------------------

    def select_candidates(self, category: str):
        """Return old, low-importance entries eligible for
        consolidation, oldest first.

        Entries already produced by a previous consolidation pass
        (TYPE: semantic) or explicitly tagged "consolidated" are never
        re-selected.
        """

        now = datetime.now()
        candidates = []

        for entry in self.memory.all(category):

            if entry["type"] == "semantic":
                continue

            if "consolidated" in [
                tag.lower() for tag in entry.get("tags", [])
            ]:
                continue

            if entry["importance"] > self.max_importance:
                continue

            try:
                age_days = (
                    now
                    - datetime.strptime(
                        entry["timestamp"], "%Y-%m-%d %H:%M:%S"
                    )
                ).days
            except ValueError:
                # Legacy/malformed timestamp: treat as old enough
                # rather than silently excluding it forever.
                age_days = self.min_age_days

            if age_days < self.min_age_days:
                continue

            candidates.append(entry)

        candidates.sort(key=lambda entry: entry["timestamp"])

        return candidates

    @staticmethod
    def _batches(candidates, batch_size):
        for start in range(0, len(candidates), batch_size):
            yield candidates[start:start + batch_size]

    # ---------------------------------------------------------
    # SUMMARIZATION (the only AI-touching step)
    # ---------------------------------------------------------

    @staticmethod
    def _build_prompt(batch):
        lines = [
            "You are helping condense a set of old, low-importance "
            "diary-style memory entries into ONE short, general "
            "semantic-knowledge summary.",
            "",
            "Rules:",
            "- Only generalize from what is explicitly written below. "
            "Do not invent facts, dates, or outcomes that are not "
            "present.",
            "- Do not claim subjective experience, consciousness, or "
            "emotion actually occurred — describe patterns in the "
            "recorded entries, not felt experience.",
            "- If the entries conflict or are too varied to "
            "generalize safely, say so explicitly instead of forcing "
            "a pattern.",
            "- Output 2-5 sentences of plain prose. No headers, no "
            "lists.",
            "",
            "Entries to condense:",
        ]

        for index, entry in enumerate(batch, start=1):
            lines.append(f"{index}. {entry['content']}")

        return "\n".join(lines)

    # ---------------------------------------------------------
    # CONSOLIDATION
    # ---------------------------------------------------------

    def consolidate_batch(
        self,
        category: str,
        batch: list,
        target_category: str = "semantic",
        archive_category: str = None,
    ):
        """Consolidate one batch of entries. Returns a report dict.

        Never raises on an unsafe or low-quality summary: it reports
        `consolidated: False` with the evaluation attached instead,
        and leaves the source entries untouched.
        """

        source_ids = [entry["id"] for entry in batch]

        if len(batch) < self.min_group_size:
            return {
                "consolidated": False,
                "reason": (
                    f"Batch has {len(batch)} entries, fewer than "
                    f"min_group_size={self.min_group_size}."
                ),
                "source_ids": source_ids,
            }

        prompt = self._build_prompt(batch)
        summary = self.provider.generate(prompt)
        evaluation = self.evaluator.evaluate(summary)

        claim_safety = evaluation["scores"]["claim_safety"]

        if claim_safety < self.min_claim_safety:
            return {
                "consolidated": False,
                "reason": (
                    "Draft summary failed the claim-safety gate "
                    f"(claim_safety {claim_safety} < "
                    f"{self.min_claim_safety}); flags: "
                    f"{evaluation['flags']}"
                ),
                "evaluation": evaluation,
                "source_ids": source_ids,
            }

        merged_tags = []

        for entry in batch:
            for tag in entry.get("tags", []):
                if tag not in merged_tags:
                    merged_tags.append(tag)

        saved = self.memory.remember(
            category=target_category,
            content=summary.strip(),
            memory_type="semantic",
            source="consolidation",
            importance=max(
                1,
                min(5, max(entry["importance"] for entry in batch)),
            ),
            tags=merged_tags,
            related=source_ids,
        )

        archive_category = archive_category or f"{category}_archived"

        for entry in batch:
            self.memory.move(
                source_category=category,
                target_category=archive_category,
                entry_id=entry["id"],
            )

        return {
            "consolidated": True,
            "summary_id": saved.get("id"),
            "target_category": target_category,
            "archive_category": archive_category,
            "source_ids": source_ids,
            "evaluation": evaluation,
        }

    def consolidate(
        self,
        category: str,
        target_category: str = "semantic",
        archive_category: str = None,
        batch_size: int = 8,
    ):
        """Run consolidation over every eligible entry in a category,
        batch_size entries at a time."""

        candidates = self.select_candidates(category)
        reports = []

        for batch in self._batches(candidates, batch_size):
            reports.append(
                self.consolidate_batch(
                    category=category,
                    batch=batch,
                    target_category=target_category,
                    archive_category=archive_category,
                )
            )

        return {
            "candidates_found": len(candidates),
            "batches": reports,
            "consolidated_count": sum(
                1 for report in reports if report["consolidated"]
            ),
        }
