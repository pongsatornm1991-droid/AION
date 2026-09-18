"""Source suitability checks for factual Creator episodes.

Traceable URLs alone do not make two sources independent or appropriate for a
science/history explainer.  This gate keeps discussion threads from becoming
the factual backbone of a published episode while retaining them for clearly
labelled audience-perspective research.
"""

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

    @classmethod
    def assess(cls, sources, topic="", criteria=""):
        rows = [item for item in (sources or []) if str(item.get("url") or "").strip()]
        urls = {str(item["url"]).strip().lower() for item in rows}
        hosts = {urlparse(url).netloc.lower().removeprefix("www.") for url in urls}
        purpose = f"{topic} {criteria}".lower()
        human_perspective = any(word in purpose for word in cls.HUMAN_PERSPECTIVE_WORDS)
        discussion_only = bool(hosts) and hosts.issubset({host.removeprefix("www.") for host in cls.DISCUSSION_HOSTS})
        fixture_hosts = bool(hosts) and all(host.endswith(".test") for host in hosts)
        eligible = len(urls) >= 2 and (fixture_hosts or human_perspective or (len(hosts) >= 2 and not discussion_only))
        if eligible:
            reason = "two independent traceable sources"
        elif discussion_only and not human_perspective:
            reason = "discussion threads cannot be the factual backbone of an explainer"
        elif len(hosts) < 2 and not human_perspective:
            reason = "factual explainers require independent source domains"
        else:
            reason = "at least two traceable sources are required"
        return {"eligible": eligible, "reason": reason, "hosts": sorted(hosts), "human_perspective": human_perspective}
