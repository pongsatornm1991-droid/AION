"""Reflection-specific uncertainty schema and evaluation pre-gate."""

import re


class ReflectionSchemaValidator:
    """Require explicit factual and cognitive uncertainty buckets."""

    SECTION_TWO = "2. What do you currently not know?"
    SECTION_THREE = "3. What would you like to understand in the future?"

    UNKNOWN_FACTS_PATTERN = re.compile(
        r"(?im)^\s*(?:[-*]\s*)?"
        r"(?:Unknown Facts|ข้อเท็จจริงที่ยังไม่ทราบ)\s*:\s*(.+?)\s*$"
    )
    COGNITIVE_PATTERN = re.compile(
        r"(?im)^\s*(?:[-*]\s*)?"
        r"(?:Cognitive Uncertainties|ความไม่แน่นอนเชิงกระบวนการคิด)"
        r"\s*:\s*(.+?)\s*$"
    )

    @classmethod
    def validate(cls, text):
        text = str(text or "").strip()
        lower = text.casefold()
        start = lower.find(cls.SECTION_TWO.casefold())
        end = lower.find(cls.SECTION_THREE.casefold())

        flags = []
        section = ""
        if start < 0:
            flags.append("Missing reflection uncertainty section.")
        else:
            section_end = end if end > start else len(text)
            section = text[start + len(cls.SECTION_TWO):section_end]

        unknown_match = cls.UNKNOWN_FACTS_PATTERN.search(section)
        cognitive_match = cls.COGNITIVE_PATTERN.search(section)

        if unknown_match is None:
            flags.append("Missing Unknown Facts subsection.")
        if cognitive_match is None:
            flags.append("Missing Cognitive Uncertainties subsection.")

        unknown_facts = (
            unknown_match.group(1).strip()
            if unknown_match is not None
            else ""
        )
        cognitive_uncertainties = (
            cognitive_match.group(1).strip()
            if cognitive_match is not None
            else ""
        )

        return {
            "valid": not flags,
            "unknown_facts": unknown_facts,
            "cognitive_uncertainties": cognitive_uncertainties,
            "flags": flags,
        }


class ReflectionSchemaEvaluator:
    """Run the schema gate before the general-purpose evaluator."""

    def __init__(self, evaluator):
        self.evaluator = evaluator

    def evaluate(self, text):
        schema = ReflectionSchemaValidator.validate(text)

        if not schema["valid"]:
            return {
                "overall_score": 1.25,
                "scores": {
                    "structure": 0,
                    "uncertainty": 0,
                    "evidence": 0,
                    "claim_safety": 5,
                },
                "flags": list(schema["flags"]),
                "length": len(str(text or "")),
                "reflection_schema": schema,
            }

        result = dict(self.evaluator.evaluate(text))
        scores = dict(result.get("scores") or {})
        scores["uncertainty"] = 5
        result["scores"] = scores
        result["overall_score"] = round(
            sum(
                float(scores.get(key, 0))
                for key in (
                    "structure",
                    "uncertainty",
                    "evidence",
                    "claim_safety",
                )
            ) / 4,
            2,
        )
        result["reflection_schema"] = schema
        return result


def filter_meta_reflection_entries(entries):
    """Remove evaluator feedback and saved reflections from new context."""

    filtered = []
    for entry in list(entries or []):
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source") or "").strip().casefold()
        content = str(entry.get("content") or "").strip().casefold()
        if source == "evaluator":
            continue
        if source == "aion" and content.startswith("aion reflection:"):
            continue
        filtered.append(entry)
    return filtered
