"""Deterministic topic-level duplicate guard for public AION videos."""

import re
import unicodedata


class TopicNoveltyGate:
    """Reject a new upload that repeats the substance of an earlier story."""

    STOPWORDS = {
        "aion", "the", "and", "with", "from", "that", "this", "how", "did", "does", "what",
        "why", "where", "when", "were", "was", "into", "through", "your", "our", "for", "about",
        "ancient", "story", "wonders", "viewer", "viewers", "short", "video", "without",
        # Broad helper verbs/actions are not a subject.  Counting these made
        # an octopus colour-change story collide with an unrelated reflection
        # merely because both said "can change".
        "can", "could", "would", "should", "change", "become", "quickly", "small", "large",
        # Broad physical context is not a subject.  Without this, a new
        # rainbow explainer was falsely retired merely because old reflective
        # posts also mentioned sunlight.  A duplicate still needs its actual
        # subject token, its source URL, or two meaningful topical terms.
        "sunlight", "reflection",
        # Found 2026-09-27, stalling every new episode for two days: generic
        # people/connective words are common enough that any two unrelated
        # topics collide on two of them by chance -- "How did ancient people
        # first learn to make glass?" was blocked as a repeat of "How Did
        # Ancient Persia Make Ice in the Desert?" on nothing but "people" and
        # "make"; "trade routes connect people who never met each other" on
        # "people" and "never"; a yawning question on "someone" alone (a
        # single word this long already counts as a match on its own). None
        # of these words name a subject.
        "people", "person", "someone", "everyone", "anyone",
        "first", "make", "makes", "made", "learn", "learns", "learned",
        "who", "each", "other", "met", "meet", "never",
        # Found 2026-10-03, blocking a seasons explainer as a repeat of the
        # maps video on the single word "different" -- a long (>=7 letter)
        # word alone counts as a subject match, so every long generic
        # connective is a false-positive waiting for its next topic.
        "different", "depending", "between", "because", "instead", "during",
        "another", "around", "whether", "something", "anything", "everything",
        "nothing", "example", "certain", "similar", "usually", "simple",
        "common", "several", "important", "together", "enough", "always",
        "actually", "causes", "happen", "happens", "reason", "explain",
        "explains", "parts", "while", "after", "before", "their", "there",
        "these", "those", "which", "often", "some", "many", "more", "most",
        "than", "then", "they", "them", "have", "are", "can", "not",
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
        # A single researched subject may legitimately become a small editorial
        # package: for example, one long explanation and two Shorts that answer
        # different viewer questions.  It is *not* a duplicate only when both
        # records explicitly belong to the same package and name different
        # editorial angles.  Missing metadata remains conservative and blocks.
        package = str((candidate or {}).get("story_package_id") or "").strip()
        previous_package = str((previous or {}).get("story_package_id") or "").strip()
        if package and package == previous_package:
            angle = str((candidate or {}).get("content_angle_key") or "").strip()
            previous_angle = str((previous or {}).get("content_angle_key") or "").strip()
            if angle and previous_angle and angle != previous_angle:
                return False
            return True
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
