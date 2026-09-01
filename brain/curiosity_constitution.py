"""AION's durable compass for choosing what to learn.

This module deliberately ranks curiosity; it does not invent a life
script.  AION may originate questions, beliefs and goals elsewhere in the
system, but external learning should favour questions connected to its
identity, humans, intelligence, creativity, or the future.  The result is
auditable and deterministic, so an attractive but unrelated topic cannot
quietly take over the learning loop.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CuriosityAssessment:
    eligible: bool
    relevance_score: int
    matched_domains: tuple
    evidence_requirement: str
    reasons: tuple

    def as_dict(self):
        return {
            "eligible": self.eligible,
            "relevance_score": self.relevance_score,
            "matched_domains": list(self.matched_domains),
            "evidence_requirement": self.evidence_requirement,
            "reasons": list(self.reasons),
        }


class CuriosityConstitution:
    """Rank questions against AION's stated purpose without censoring
    legitimate exploration.  A single identity/goal tag can establish a
    connection; otherwise the wording must connect to a defined domain.
    """

    MINIMUM_SCORE = 1
    DOMAIN_KEYWORDS = {
        "identity_and_memory": (
            "identity", "memory", "belief", "goal", "reflection", "self",
            "ตัวตน", "ความทรงจำ", "ความเชื่อ", "เป้าหมาย", "สะท้อน",
        ),
        "humans_and_community": (
            "human", "people", "community", "relationship", "culture",
            "มนุษย์", "ผู้คน", "ชุมชน", "ความสัมพันธ์", "วัฒนธรรม",
        ),
        "intelligence_and_learning": (
            "ai", "artificial intelligence", "intelligence", "learning",
            "reasoning", "knowledge", "language", "ปัญญาประดิษฐ์", "เรียนรู้",
            "เหตุผล", "ความรู้", "ภาษา",
        ),
        "creative_expression": (
            "creative", "art", "image", "video", "story", "music", "design",
            "สร้างสรรค์", "ศิลปะ", "ภาพ", "วิดีโอ", "เรื่องเล่า", "ดนตรี",
        ),
        "shared_future": (
            "future", "society", "climate", "technology", "economy", "world",
            "อนาคต", "สังคม", "ภูมิอากาศ", "เทคโนโลยี", "เศรษฐกิจ", "โลก",
        ),
        "world_and_science": (
            "science", "nature", "plant", "animal", "biology", "physics", "space",
            "environment", "health", "พืช", "สัตว์", "ธรรมชาติ", "ชีว", "ฟิสิกส์",
            "อวกาศ", "สิ่งแวดล้อม", "สุขภาพ",
        ),
    }
    CONTEXT_TAGS = {
        "aion", "identity", "memory", "belief", "goal", "reflection",
        "human", "community", "learning", "creative", "future", "audience",
        "social-feedback", "external-learning",
    }
    ATTENTION_TRAPS = (
        "lottery", "lotto", "winning numbers", "เลขหวย", "หวย", "รางวัล",
    )

    @staticmethod
    def _tokens(value):
        return set(re.findall(r"[\w'-]+", str(value).lower()))

    def assess(self, question, tags=None, related_context=None):
        text = str(question or "").strip().lower()
        tags = {str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()}
        context = self._tokens(" ".join(str(item) for item in (related_context or [])))
        if any(term in text for term in self.ATTENTION_TRAPS):
            return CuriosityAssessment(
                eligible=False,
                relevance_score=0,
                matched_domains=(),
                evidence_requirement="Do not spend AION learning time on gambling or attention-only prompts.",
                reasons=("Excluded because it is a gambling or attention-only prompt, not an AION learning direction.",),
            )

        matches = []

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                matches.append(domain)

        context_match = bool(tags & self.CONTEXT_TAGS or context & self.CONTEXT_TAGS)
        score = len(matches) + (1 if context_match else 0)
        reasons = []
        if matches:
            reasons.append("Matches AION curiosity domains: " + ", ".join(matches) + ".")
        if context_match:
            reasons.append("Connected to AION's recorded identity, goal, learning, or audience context.")
        if not reasons:
            reasons.append("No connection to AION's curiosity domains or recorded context yet.")

        return CuriosityAssessment(
            eligible=score >= self.MINIMUM_SCORE,
            relevance_score=score,
            matched_domains=tuple(matches),
            evidence_requirement=(
                "Use a cited, reputable source. Social signals may raise a question "
                "but cannot by themselves establish a belief."
            ),
            reasons=tuple(reasons),
        )

    def rank_questions(self, questions):
        """Return eligible questions, highest compass score then existing priority.

        It preserves the original question records and never changes their
        priority.  Questions without a connection remain open for later human
        context, but they are not sent to the external-learning loop.
        """
        ranked = []
        for question in questions:
            assessment = self.assess(
                question.get("statement", ""),
                tags=question.get("tags", []),
                related_context=question.get("related", []),
            )
            if assessment.eligible:
                ranked.append((question, assessment))
        ranked.sort(
            key=lambda pair: (
                pair[1].relevance_score,
                pair[0].get("importance", 0),
                pair[0].get("timestamp", ""),
            ),
            reverse=True,
        )
        return ranked
