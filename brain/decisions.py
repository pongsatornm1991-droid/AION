from .auditor import CognitiveAuditor
from .decision import DecisionEngine


class DecisionHistory:
    """Read and promote persisted AION decision records."""

    ACCEPTED = "decisions_accepted"
    PENDING = "decisions_pending_verification"

    def __init__(self, memory):
        self.memory = memory

    def list(self, status="all", limit=10):
        categories = []

        if status in ("accepted", "all"):
            categories.append(("ACCEPTED", self.ACCEPTED))

        if status in ("pending", "all"):
            categories.append(("NEEDS_VERIFICATION", self.PENDING))

        records = []

        for label, category in categories:
            for entry in self.memory.all(category):
                records.append({
                    **entry,
                    "status": label,
                    "category": category,
                })

        records.sort(
            key=lambda entry: entry["timestamp"],
            reverse=True,
        )

        return records[:max(0, limit)]

    def promote(self, entry_id, additional_facts):
        """Re-audit a pending decision and promote it only when safe.

        entry_id must be the stable id shown by list()/history, not a
        timestamp: two decisions can be recorded in the same second,
        so timestamp text is never a reliable lookup key.
        """

        matches = [
            entry
            for entry in self.memory.all(self.PENDING)
            if entry["id"] == entry_id
        ]

        if not matches:
            raise ValueError(
                "No pending decision matches the supplied id."
            )

        if len(matches) > 1:
            raise ValueError(
                "More than one pending decision matches the supplied id."
            )

        record = self._parse(matches[0]["content"])
        facts = record["facts"] + self._clean_items(additional_facts)

        decision = DecisionEngine().evaluate(
            question=record["question"],
            options=record["options"],
            facts=facts,
            inferences=record["inferences"],
            uncertainties=record["uncertainties"],
        )
        audit = CognitiveAuditor().audit(
            question=record["question"],
            conclusion=record["conclusion"],
            facts=facts,
            inferences=record["inferences"],
            uncertainties=record["uncertainties"],
        )

        if audit["risk"] != "LOW" or not audit["auditable"]:
            return {
                "promoted": False,
                "decision": decision,
                "audit": audit,
            }

        content = self._format_record(
            decision=decision,
            audit=audit,
            conclusion=record["conclusion"],
            verification_facts=additional_facts,
        )

        moved = self.memory.move(
            source_category=self.PENDING,
            target_category=self.ACCEPTED,
            entry_id=entry_id,
            content=content,
            importance=3,
        )

        return {
            "promoted": True,
            "decision": decision,
            "audit": audit,
            "record": moved,
        }

    def _parse(self, content):
        fields = {
            "question": "",
            "conclusion": "",
            "options": [],
            "facts": [],
            "inferences": [],
            "uncertainties": [],
        }
        section_map = {
            "Options:": "options",
            "Facts:": "facts",
            "Inferences:": "inferences",
            "Uncertainties:": "uncertainties",
        }
        current_section = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if line.startswith("Question:"):
                fields["question"] = line.removeprefix("Question:").strip()
                current_section = None
            elif line.startswith("Conclusion:"):
                fields["conclusion"] = line.removeprefix("Conclusion:").strip()
                current_section = None
            elif line in section_map:
                current_section = section_map[line]
            elif current_section and line.startswith("- "):
                value = line[2:].strip()
                if value and value != "None":
                    fields[current_section].append(value)

        if not fields["question"] or not fields["conclusion"]:
            raise ValueError(
                "Pending decision record is missing its question or conclusion."
            )

        return fields

    def _format_record(
        self,
        decision,
        audit,
        conclusion,
        verification_facts,
    ):
        return "\n".join([
            "AION Decision Record",
            "",
            "Status: ACCEPTED",
            f"Question: {decision['question']}",
            f"Conclusion: {conclusion}",
            f"Confidence: {decision['confidence']:.2f}",
            f"Audit risk: {audit['risk']}",
            f"Auditable: {audit['auditable']}",
            "",
            "Options:",
            self._format_items(decision["options"]),
            "",
            "Facts:",
            self._format_items(decision["facts"]),
            "",
            "Inferences:",
            self._format_items(decision["inferences"]),
            "",
            "Uncertainties:",
            self._format_items(decision["uncertainties"]),
            "",
            "Verification facts added:",
            self._format_items(self._clean_items(verification_facts)),
            "",
            "Recommendations:",
            self._format_items(audit["recommendations"]),
        ])

    @staticmethod
    def _clean_items(items):
        return [
            str(item).strip()
            for item in items or []
            if str(item).strip()
        ]

    @staticmethod
    def _format_items(items):
        if not items:
            return "- None"

        return "\n".join(
            f"- {item}"
            for item in items
        )
