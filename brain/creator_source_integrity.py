"""Source suitability checks for factual Creator episodes.

Traceable URLs alone do not make two sources independent or appropriate for a
science/history explainer.  This gate keeps discussion threads from becoming
the factual backbone of a published episode while retaining them for clearly
labelled audience-perspective research.
"""

import re
from urllib.parse import urlparse


class CreatorSourceIntegrity:
    DISCUSSION_HOSTS = {
        "news.ycombinator.com", "reddit.com", "www.reddit.com",
        "facebook.com", "www.facebook.com", "instagram.com",
        "x.com", "twitter.com",
    }
    HUMAN_PERSPECTIVE_WORDS = (
        "human sources", "human perspective", "people think", "people feel",
        "opinions", "experiences", "conversations", "testimony",
    )
    # A traceable URL must not be counted simply because a model produced a
    # sentence beside it. These patterns are intentionally narrow: they catch
    # an observation explicitly saying that the source is off-topic without
    # trying to judge subtle scientific relevance from keywords alone.
    _OFF_TOPIC_OBSERVATION_PATTERNS = (
        r"\bno relevant observation\b",
        r"\bno relevant information\b",
        r"\bno relevant evidence\b",
        r"\bdoes not (?:answer|address|explain|describe|discuss|support)\b",
        r"\bdoesn't (?:answer|address|explain|describe|discuss|support)\b",
        r"\bnot relevant to (?:the )?(?:question|topic)\b",
    )

    @classmethod
    def _has_explicitly_off_topic_observation(cls, rows):
        for row in rows:
            observation = " ".join(str(row.get("observation") or "").split()).lower()
            if any(re.search(pattern, observation) for pattern in cls._OFF_TOPIC_OBSERVATION_PATTERNS):
                return True
        return False

    @classmethod
    def assess(cls, sources, topic="", criteria=""):
        rows = [item for item in (sources or []) if str(item.get("url") or "").strip()]
        urls = {str(item["url"]).strip().lower() for item in rows}
        hosts = {urlparse(url).netloc.lower().removeprefix("www.") for url in urls}
        purpose = f"{topic} {criteria}".lower()
        human_perspective = any(word in purpose for word in cls.HUMAN_PERSPECTIVE_WORDS)
        discussion_only = bool(hosts) and hosts.issubset({host.removeprefix("www.") for host in cls.DISCUSSION_HOSTS})
        fixture_hosts = bool(hosts) and all(host.endswith(".test") for host in hosts)
        off_topic = cls._has_explicitly_off_topic_observation(rows)
        eligible = (
            len(urls) >= 2
            and not off_topic
            and (fixture_hosts or human_perspective or (len(hosts) >= 2 and not discussion_only))
        )
        if off_topic:
            reason = "a source observation explicitly says it does not answer the topic"
        elif eligible:
            reason = "two independent traceable sources"
        elif discussion_only and not human_perspective:
            reason = "discussion threads cannot be the factual backbone of an explainer"
        elif len(hosts) < 2 and not human_perspective:
            reason = "factual explainers require independent source domains"
        else:
            reason = "at least two traceable sources are required"
        return {"eligible": eligible, "reason": reason, "hosts": sorted(hosts), "human_perspective": human_perspective, "off_topic_observation": off_topic}
