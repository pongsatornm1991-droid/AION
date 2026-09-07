"""AION Phase 5F.4 — deterministic evidence qualification.

Purpose
-------
A retrieved source is not automatically useful evidence.

This gate runs after AION drafts an observation from a source but
before that observation is persisted as qualifying research evidence.

It deliberately does NOT:
- call Gemini or any other AI provider
- access the network
- write memory
- mutate curiosity questions
- consume attempts
- replace the Completion Criteria Gate

The gate is intentionally conservative. In particular, if AION's own
draft explicitly says that the source does not answer or support the
research question, that draft must not count as evidence.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class EvidenceQualificationGate:
    """Deterministic gate for one drafted research observation."""

    _MIN_OBSERVATION_LENGTH = 30

    _SELF_DISQUALIFYING_PATTERNS = (
        r"\bthere is no information\b",
        r"\bthere is not enough information\b",
        r"\bno information (?:is )?provided\b",
        r"\bdoes not (?:answer|address|explain|provide|show|support)\b",
        r"\bdoesn't (?:answer|address|explain|provide|show|support)\b",
        r"\bdoes not contain\b",
        r"\bdoesn't contain\b",
        r"\bdoes not discuss\b",
        r"\bdoesn't discuss\b",
        r"\bdoes not tell us\b",
        r"\bdoesn't tell us\b",
        r"\bdoes not provide evidence\b",
        r"\bdoesn't provide evidence\b",
        r"\bdoes not provide information\b",
        r"\bdoesn't provide information\b",
        r"\bdoes not provide insight\b",
        r"\bdoesn't provide insight\b",
        r"\bsource is insufficient\b",
        r"\binsufficient evidence\b",
        r"\binsufficient information\b",
        r"\bnot enough evidence\b",
        r"\bnot enough information\b",
        r"\bcannot determine\b",
        r"\bcannot conclude\b",
        r"\bcan't determine\b",
        r"\bcan't conclude\b",
        r"\bnot supported by (?:the )?source\b",
        r"\bnot addressed by (?:the )?source\b",
        r"\bsource only (?:discusses|describes|focuses on|mentions)\b",
        r"\binstead focuses on\b",
        r"\binstead discusses\b",
    )

    @classmethod
    def observation_self_disqualifies(
        cls,
        observation: Any,
    ) -> bool:
        """Return True when the observation rejects its own usefulness."""

        text = str(
            observation or ""
        ).strip()

        if not text:
            return True

        if len(text) < cls._MIN_OBSERVATION_LENGTH:
            return True

        normalized = re.sub(
            r"\s+",
            " ",
            text.lower(),
        )

        for pattern in cls._SELF_DISQUALIFYING_PATTERNS:
            if re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            ):
                return True

        return False

    _HUMAN_INTERPRETATION_PATTERNS = (
        r"(?:^|[.!?]\s+)(?:this|that)\s+suggests\b",
        r"(?:^|[.!?]\s+)(?:this|that)\s+illustrates\b",
        r"(?:^|[.!?]\s+)(?:this|that)\s+demonstrates\b",
        r"(?:^|[.!?]\s+)(?:this|that)\s+shows\s+that\b",
        r"(?:^|[.!?]\s+)(?:this|that)\s+means\s+that\b",
        r"(?:^|[.!?]\s+)therefore\b",
        r"(?:^|[.!?]\s+)thus\b",
        r"(?:^|[.!?]\s+)consequently\b",
        r"(?:^|[.!?]\s+)hence\b",
        r"^\s*based\s+on\b.{0,160}\b(?:an?\s+ai|aion)\s+(?:can|could|should|may|might)\b",
        r"(?:^|[.!?]\s+)(?:an?\s+ai|aion)\s+(?:can|could|should|may|might)\s+learn\b",
        r"(?:^|[.!?]\s+)for\s+aion\b",
    )

    _HUMAN_ATTRIBUTION_PATTERNS = (
        r"^\s*the\s+commenter\s+",
        r"^\s*the\s+author\s+",
        r"^\s*the\s+writer\s+",
        r"^\s*the\s+participant\s+",
        r"^\s*the\s+speaker\s+",
        r"^\s*the\s+person\s+",
        r"^\s*the\s+source\s+",
        r"^\s*according\s+to\s+",
        r"^\s*in\s+the\s+(?:comment|post|discussion|source)\b",
        r"^\s*a\s+(?:commenter|participant|developer|user)\s+",
    )

    @classmethod
    def human_observation_is_interpretive(
        cls,
        observation: Any,
    ) -> bool:
        """
        Return True when a human-perspective observation
        appears to contain AION interpretation instead
        of only the traceable person's perspective.
        """

        text = str(
            observation or ""
        ).strip()

        if not text:
            return True

        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        for pattern in (
            cls._HUMAN_INTERPRETATION_PATTERNS
        ):
            if re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            ):
                return True

        return False

    @classmethod
    def human_observation_has_attribution(
        cls,
        observation: Any,
    ) -> bool:
        """
        Return True when a human-perspective observation
        is explicitly framed as a report of the human
        source's own view or experience.
        """

        text = str(
            observation or ""
        ).strip()

        if not text:
            return False

        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        for pattern in (
            cls._HUMAN_ATTRIBUTION_PATTERNS
        ):
            if re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            ):
                return True

        return False


    _HUMAN_FIDELITY_RISK_FAMILIES = (
        (
            "intent",
            (
                "intentional",
                "intentionally",
                "deliberate",
                "deliberately",
            ),
        ),
        (
            "certainty",
            (
                "certain",
                "certainly",
                "definite",
                "definitely",
                "undoubted",
                "undoubtedly",
                "inevitable",
                "inevitably",
            ),
        ),
        (
            "clarity",
            (
                "clear",
                "clearly",
                "obvious",
                "obviously",
            ),
        ),
        (
            "evaluation",
            (
                "incredible",
                "incredibly",
                "remarkable",
                "remarkably",
                "extraordinary",
                "extraordinarily",
            ),
        ),
        (
            "strictness",
            (
                "strict",
                "strictly",
                "pure",
                "purely",
            ),
        ),
        (
            "absolute",
            (
                "always",
                "never",
            ),
        ),
    )

    @staticmethod
    def _normalized_words(
        value: Any,
    ):
        return set(
            re.findall(
                r"[a-zA-Z]+",
                str(
                    value or ""
                ).lower(),
            )
        )

    @classmethod
    def human_observation_has_unsupported_fidelity_markers(
        cls,
        observation: Any,
        source_extract: Any,
    ) -> bool:
        """
        Conservatively reject wording inflation.

        This is deliberately narrow. It is not a
        semantic-entailment engine.

        For selected high-risk concepts, a human
        observation may use that concept only when
        the raw source also contains a member of
        the same concept family.

        Missing raw-source text preserves backward
        compatibility for legacy callers.
        """

        observation_words = (
            cls._normalized_words(
                observation
            )
        )

        source_words = (
            cls._normalized_words(
                source_extract
            )
        )

        if not observation_words:
            return False

        if not source_words:
            return False

        for (
            _family_name,
            family_words,
        ) in cls._HUMAN_FIDELITY_RISK_FAMILIES:
            observation_has_family = any(
                word in observation_words
                for word in family_words
            )

            if not observation_has_family:
                continue

            source_has_family = any(
                word in source_words
                for word in family_words
            )

            if not source_has_family:
                return True

        return False

    @staticmethod
    def _traceable_url(
        url: Any,
    ) -> bool:
        value = str(
            url or ""
        ).strip().lower()

        return (
            value.startswith("https://")
            or value.startswith("http://")
        )

    def evaluate(
        self,
        *,
        question: Any,
        criteria: Any = None,
        evidence_type: Optional[str] = None,
        source_kind: Any = None,
        title: Any = None,
        url: Any = None,
        source_extract: Any = None,
        observation: Any = None,
    ) -> Dict[str, Any]:
        """Return a deterministic qualification report."""

        question_text = str(
            question or ""
        ).strip()

        observation_text = str(
            observation or ""
        ).strip()

        source_extract_text = str(
            source_extract or ""
        ).strip()

        evidence_type_text = str(
            evidence_type or ""
        ).strip().lower()

        source_kind_text = str(
            source_kind or ""
        ).strip()

        title_text = str(
            title or ""
        ).strip()

        url_text = str(
            url or ""
        ).strip()

        if not question_text:
            return {
                "qualified": False,
                "reason": "Research question is empty.",
            }

        if not observation_text:
            return {
                "qualified": False,
                "reason": "Observation is empty.",
            }

        if self.observation_self_disqualifies(
            observation_text
        ):
            return {
                "qualified": False,
                "reason": (
                    "The drafted observation explicitly indicates "
                    "that this source does not provide usable "
                    "evidence for the research question."
                ),
            }

        if evidence_type_text == "human_perspective":
            if self.human_observation_is_interpretive(
                observation_text
            ):
                return {
                    "qualified": False,
                    "reason": (
                        "Human-perspective observation mixes the "
                        "source perspective with interpretation or "
                        "a conclusion that belongs in synthesis."
                    ),
                }

            if not self.human_observation_has_attribution(
                observation_text
            ):
                return {
                    "qualified": False,
                    "reason": (
                        "Human-perspective observation is not "
                        "explicitly attributed to the traceable "
                        "human source."
                    ),
                }

            if self.human_observation_has_unsupported_fidelity_markers(
                observation_text,
                source_extract_text,
            ):
                return {
                    "qualified": False,
                    "reason": (
                        "Human-perspective observation failed "
                        "the grounded fidelity check because "
                        "it introduces unsupported intent, "
                        "certainty, evaluation, emphasis, "
                        "or absolutes not present in the source."
                    ),
                }

            if not title_text:
                return {
                    "qualified": False,
                    "reason": (
                        "Human-perspective evidence has no "
                        "traceable source title."
                    ),
                }

            if not self._traceable_url(
                url_text
            ):
                return {
                    "qualified": False,
                    "reason": (
                        "Human-perspective evidence has no "
                        "traceable HTTP(S) source URL."
                    ),
                }

        return {
            "qualified": True,
            "reason": (
                "Observation passed deterministic "
                "evidence qualification."
            ),
            "question": question_text,
            "criteria": str(
                criteria or ""
            ).strip(),
            "evidence_type": evidence_type_text,
            "source_kind": source_kind_text,
            "title": title_text,
            "url": url_text,
        }
