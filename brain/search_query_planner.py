"""Evidence-aware search query planning for AION.

Phase 5F.3
Phase 5F.5E semantic search refinement

AION's internal curiosity questions are written for reasoning, not for
search engines. Sending a complete natural-language question directly
to an external search API can easily produce zero results even when
relevant material exists.

SearchQueryPlanner converts a question plus its required evidence type
into a small bounded collection of search-oriented queries.

Phase 5F.5E adds semantic query families for questions where the
research target is not merely the literal topic vocabulary.

For example, a human-perspective question contrasting factual
knowledge with what people learn through experience should search for
concepts such as tacit knowledge, judgment, intuition, mentorship,
lived experience, and difficult-to-articulate knowledge rather than
only searching for generic "AI human learning" discussions.

Important boundaries

This planner:

- does NOT access the network
- does NOT call an AI provider
- does NOT decide whether evidence is true
- does NOT modify memory
- does NOT resolve curiosity questions
- does NOT consume attempts

Its only responsibility is query formulation.

External search results remain untrusted evidence and must still pass
AION's normal evidence, synthesis, safety, and completion gates.
"""

from __future__ import annotations

import re
from typing import Iterable


class SearchQueryPlanner:
    """Create bounded search-engine-oriented queries."""

    MAX_QUERIES = 5

    _STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "being",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "may",
        "might",
        "of",
        "on",
        "or",
        "should",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
    }

    _NORMALIZATION = {
        "artificial intelligence": "AI",
        "artificial-intelligence": "AI",
        "humans": "human",
        "people": "human",
        "persons": "human",
        "teaches": "teach",
        "teaching": "teach",
        "taught": "teach",
        "learns": "learn",
        "learned": "learn",
        "learning": "learning",
        "experiences": "experience",
        "perspectives": "perspective",
        "opinions": "opinion",
        "facts": "facts",
    }

    _HUMAN_PERSPECTIVE_SEEDS = (
        "human experience",
        "human perspective",
        "personal experience",
        "human judgment",
        "lived experience",
    )

    _SOCIAL_SIGNAL_SEEDS = (
        "public opinion",
        "community discussion",
        "user experience",
        "people discussing",
    )

    # Phase 5F.5E
    #
    # These are concepts describing knowledge that depends on
    # experience, judgment, social context, practice, or articulation.
    #
    # They are deliberately topic-independent. They are not tied to one
    # curiosity question or to AI specifically.
    _EXPERIENTIAL_KNOWLEDGE_QUERIES = (
        "tacit knowledge experience",
        "knowledge difficult to articulate",
        "human judgment experience",
        "intuition learned through experience",
        "lessons from lived experience",
    )

    def plan(
        self,
        question: str,
        evidence_type: str | None = None,
        max_queries: int | None = None,
    ) -> list[str]:
        """Return a bounded list of search queries.

        The original question may contribute vocabulary, but the
        complete sentence is deliberately not used as the only query.
        """

        question = str(
            question or ""
        ).strip()

        evidence_type = str(
            evidence_type or ""
        ).strip()

        if not question:
            return []

        limit = (
            self.MAX_QUERIES
            if max_queries is None
            else max(
                1,
                min(
                    int(max_queries),
                    self.MAX_QUERIES,
                ),
            )
        )

        normalized = self._normalize_text(
            question
        )

        keywords = self._keywords(
            normalized
        )

        topic_terms = self._topic_terms(
            keywords
        )

        candidates: list[str] = []

        if evidence_type == "human_perspective":
            candidates.extend(
                self._human_perspective_queries(
                    normalized,
                    topic_terms,
                )
            )

        elif evidence_type == "social_signal":
            candidates.extend(
                self._social_signal_queries(
                    topic_terms
                )
            )

        else:
            candidates.extend(
                self._general_queries(
                    topic_terms
                )
            )

        # Add a compact literal-topic fallback only after semantic
        # candidates. This preserves topic coverage without allowing
        # broad literal vocabulary to dominate the search plan.
        compact = " ".join(
            topic_terms[:5]
        ).strip()

        if compact:
            candidates.append(
                compact
            )

        return self._deduplicate(
            candidates,
            limit=limit,
        )

    # --------------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------------

    def _normalize_text(
        self,
        text: str,
    ) -> str:
        normalized = text

        # Longest source strings first prevents a shorter mapping from
        # partially consuming a longer phrase.
        normalization_items = sorted(
            self._NORMALIZATION.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for source, replacement in normalization_items:
            normalized = re.sub(
                rf"\b{re.escape(source)}\b",
                replacement,
                normalized,
                flags=re.IGNORECASE,
            )

        normalized = re.sub(
            r"[^\w\s-]",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized.strip()

    def _keywords(
        self,
        text: str,
    ) -> list[str]:
        tokens = re.findall(
            r"[A-Za-z0-9_-]+",
            text,
        )

        result = []

        for token in tokens:
            lowered = token.lower()

            if lowered in self._STOP_WORDS:
                continue

            if len(lowered) < 2:
                continue

            if lowered == "ai":
                token = "AI"

            else:
                token = lowered

            if token not in result:
                result.append(
                    token
                )

        return result

    # --------------------------------------------------------
    # TOPIC EXTRACTION
    # --------------------------------------------------------

    def _topic_terms(
        self,
        keywords: Iterable[str],
    ) -> list[str]:
        terms = list(
            keywords
        )

        result = []

        # AI is useful search context and should normally come first.
        if "AI" in terms:
            result.append(
                "AI"
            )

        for term in terms:
            if term == "AI":
                continue

            if term in {
                "facts",
                "fact",
                "alone",
                "cannot",
                "teach",
            }:
                continue

            result.append(
                term
            )

        result = [
            (
                "learning"
                if term == "learn"
                else term
            )
            for term in result
        ]

        return result

    # --------------------------------------------------------
    # SEMANTIC INTENT DETECTION
    # --------------------------------------------------------

    def _is_experiential_knowledge_question(
        self,
        normalized_question: str,
        topic_terms: list[str],
    ) -> bool:
        """Detect questions contrasting facts with human experience.

        This is deliberately semantic-family detection rather than an
        exact-question match.

        Signals include:

        - factual/informational knowledge
        - learning/teaching/knowing
        - human or experiential perspective
        - contrast language such as "alone", "cannot", or "beyond"

        A sufficient combination activates the experiential/tacit
        knowledge query family.
        """

        lowered = normalized_question.lower()

        has_fact_signal = any(
            term in lowered
            for term in (
                "fact",
                "facts",
                "factual",
                "information",
            )
        )

        has_learning_signal = any(
            term in lowered
            for term in (
                "learn",
                "learning",
                "teach",
                "knowledge",
                "know",
            )
        )

        has_human_signal = any(
            term in lowered
            for term in (
                "human",
                "experience",
                "perspective",
                "people",
                "person",
            )
        )

        has_contrast_signal = any(
            term in lowered
            for term in (
                "alone",
                "cannot",
                "can't",
                "beyond",
                "more than",
                "not enough",
            )
        )

        # Some normalization paths may remove literal wording from the
        # topic list, so retain a secondary structural signal.
        topic_has_human = any(
            term in {
                "human",
                "experience",
                "perspective",
            }
            for term in topic_terms
        )

        return (
            has_fact_signal
            and has_learning_signal
            and (
                has_human_signal
                or topic_has_human
            )
            and has_contrast_signal
        )

    # --------------------------------------------------------
    # HUMAN-PERSPECTIVE QUERIES
    # --------------------------------------------------------

    def _human_perspective_queries(
        self,
        normalized_question: str,
        topic_terms: list[str],
    ) -> list[str]:
        queries = []

        # Phase 5F.5E:
        # semantic intent takes precedence over broad literal matching.
        #
        # This prevents questions about what factual knowledge cannot
        # convey from collapsing into generic AI-vs-human-learning
        # searches.
        if self._is_experiential_knowledge_question(
            normalized_question,
            topic_terms,
        ):
            queries.extend(
                self._EXPERIENTIAL_KNOWLEDGE_QUERIES
            )

            return queries

        has_ai = any(
            term == "AI"
            for term in topic_terms
        )

        has_learning = any(
            term in {
                "learn",
                "learning",
            }
            for term in topic_terms
        )

        has_human = any(
            term == "human"
            for term in topic_terms
        )

        # Preserve the Phase 5F.3 broad AI/human-learning family for
        # questions that really are about AI-vs-human learning and do
        # not carry the experiential/factual contrast detected above.
        if (
            has_ai
            and has_human
            and has_learning
        ):
            queries.extend([
                "AI human learning",
                "human experience AI",
                "AI learning from humans",
                "human judgment AI",
                "lived experience AI",
            ])

            return queries

        core = self._core_topic(
            topic_terms
        )

        if core:
            for seed in (
                self._HUMAN_PERSPECTIVE_SEEDS
            ):
                queries.append(
                    f"{core} {seed}"
                )

        else:
            queries.extend(
                self._HUMAN_PERSPECTIVE_SEEDS
            )

        return queries

    # --------------------------------------------------------
    # SOCIAL SIGNAL QUERIES
    # --------------------------------------------------------

    def _social_signal_queries(
        self,
        topic_terms: list[str],
    ) -> list[str]:
        core = self._core_topic(
            topic_terms
        )

        if not core:
            return list(
                self._SOCIAL_SIGNAL_SEEDS
            )

        return [
            f"{core} {seed}"
            for seed in self._SOCIAL_SIGNAL_SEEDS
        ]

    # --------------------------------------------------------
    # GENERAL QUERY PLANNING
    # --------------------------------------------------------

    def _general_queries(
        self,
        topic_terms: list[str],
    ) -> list[str]:
        if not topic_terms:
            return []

        queries = []

        queries.append(
            " ".join(
                topic_terms[:5]
            )
        )

        if len(topic_terms) > 3:
            queries.append(
                " ".join(
                    topic_terms[:3]
                )
            )

        if (
            "AI" in topic_terms
            and len(topic_terms) > 1
        ):
            non_ai = [
                term
                for term in topic_terms
                if term != "AI"
            ]

            queries.append(
                "AI "
                + " ".join(
                    non_ai[:3]
                )
            )

        return queries

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _core_topic(
        self,
        topic_terms: list[str],
    ) -> str:
        if not topic_terms:
            return ""

        useful = []

        for term in topic_terms:
            if term in {
                "human",
                "perspective",
                "experience",
                "opinion",
            }:
                continue

            useful.append(
                term
            )

        if not useful:
            useful = topic_terms

        return " ".join(
            useful[:3]
        )

    def _deduplicate(
        self,
        queries: Iterable[str],
        limit: int,
    ) -> list[str]:
        result = []
        seen = set()

        for query in queries:
            cleaned = re.sub(
                r"\s+",
                " ",
                str(
                    query or ""
                ).strip(),
            )

            if not cleaned:
                continue

            key = cleaned.lower()

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                cleaned
            )

            if len(result) >= limit:
                break

        return result
