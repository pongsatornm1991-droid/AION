"""Deterministic topic-level duplicate guard for public AION videos."""

import re
import unicodedata


class TopicNoveltyGate:
    """Reject a new upload that repeats the substance of an earlier story."""

    STOPWORDS = {
        "aion", "the", "and", "with", "from", "that", "this", "how", "did", "does", "what",
        "why", "where", "when", "were", "was", "into", "through", "your", "our", "for", "about",
        "ancient", "story", "wonders", "viewer", "viewers", "short", "video", "without",
    }

    @classmethod
    def tokens(cls, payload):
        explicit = str((payload or {}).get("topic_key") or "")
        text = explicit or " ".join(str((payload or {}).get(key) or "") for key in ("title", "caption", "wonder_hook"))
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
        return {
            token for token in re.findall(r"[a-z0-9]{3,}", text)
            if token not in cls.STOPWORDS
        }

    @classmethod
    def same_topic(cls, candidate, previous):
        candidate_urls = set(candidate.get("source_urls") or [])
        previous_urls = set(previous.get("source_urls") or [])
        if candidate_urls and previous_urls and candidate_urls.intersection(previous_urls):
            return True
        current, earlier = cls.tokens(candidate), cls.tokens(previous)
        overlap = current.intersection(earlier)
        if not overlap:
            return False
        # One unusual, long subject token (for example "yakhchal") is enough;
        # otherwise require two shared topical terms so generic history words
        # do not block genuinely different stories.
        return any(len(token) >= 7 for token in overlap) or len(overlap) >= 2
