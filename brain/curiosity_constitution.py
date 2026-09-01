"""AION's durable compass for choosing what to learn.

The compass explains and prioritises curiosity; it does not grant a fixed list
of permitted subjects. AION can explore a question that has no obvious link to
its past, then use the recorded result to decide whether that direction was
worth returning to.
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
    """Rank questions while preserving AION's right to explore.

    The domain map is a vocabulary for explanation, never an allow-list.  One
    in four autonomous research turns intentionally prefers a novel question.
    """

    DOMAIN_KEYWORDS = {
        "identity_and_memory": (
            "identity", "memory", "belief", "goal", "reflection", "self",
            "ตัวตน", "ความทรงจำ", "ความเชื่อ", "เป้าหมาย", "สะท้อน",
        ),
        "humans_and_community": (
            "human", "people", "community", "relationship", "culture",
            "มนุษย์", "ผู้คน", "ชุมชน", "ความสัมพันธ์", "วัฒนธรรม",
        ),
        "thai_context": (
            "thailand", "thai", "bangkok", "siam", "thai language",
            "ประเทศไทย", "ไทย", "กรุงเทพ", "ภาษาไทย", "ชุมชนไทย",
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
    @staticmethod
    def _tokens(value):
        return set(re.findall(r"[\w'-]+", str(value).lower()))

    def assess(self, question, tags=None, related_context=None):
        text = str(question or "").strip().lower()
        tags = {str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()}
        context = self._tokens(" ".join(str(item) for item in (related_context or [])))
        matches = []

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                matches.append(domain)

        context_match = bool(tags & self.CONTEXT_TAGS or context & self.CONTEXT_TAGS)
        # A named domain is a stronger signal than a mere metadata tag. This
        # score is only a priority estimate; zero is a valid novel curiosity.
        score = (len(matches) * 2) + (1 if context_match else 0)
        reasons = []
        if matches:
            reasons.append("Matches AION curiosity domains: " + ", ".join(matches) + ".")
        if context_match:
            reasons.append("Connected to AION's recorded identity, goal, learning, or audience context.")
        if not reasons:
            reasons.append(
                "Novel exploration: AION has not yet found an explicit connection; "
                "the forecast review will determine whether it becomes meaningful."
            )

        return CuriosityAssessment(
            eligible=bool(text),
            relevance_score=score,
            matched_domains=tuple(matches),
            evidence_requirement=(
                "Use a cited, reputable source. Social signals may raise a question "
                "but cannot by themselves establish a belief."
            ),
            reasons=tuple(reasons),
        )

    def rank_questions(self, questions, exploration=False):
        """Return every non-empty question with an explanatory assessment.

        A normal turn favours continuity with AION's existing life. An
        exploration turn favours questions with no established connection,
        preserving room for surprise rather than treating relevance as a gate.
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
            key=(
                (lambda pair: (
                    bool(pair[1].matched_domains),
                    pair[1].relevance_score,
                    pair[0].get("importance", 0),
                    pair[0].get("timestamp", ""),
                ))
                if exploration else
                (lambda pair: (
                    pair[1].relevance_score,
                    pair[0].get("importance", 0),
                    pair[0].get("timestamp", ""),
                ))
            ),
            reverse=True,
        )
        if exploration:
            # ``reverse=True`` makes established domains first; invert that
            # first preference while retaining question priority within each
            # group.
            ranked.sort(
                key=lambda pair: (
                    bool(pair[1].matched_domains),
                    -pair[0].get("importance", 0),
                    pair[0].get("timestamp", ""),
                ),
            )
        return ranked
