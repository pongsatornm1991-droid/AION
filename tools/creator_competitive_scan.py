"""On-demand competitive discovery scan for AION's own content niche.

Uses the YouTube Data API (read-only, public metadata only -- title, channel,
view count) so AION can see what similar creators are currently publishing
and how those uploads are performing, without downloading any protected
expression. This turns the `youtube_discovery` source in
core/source_registry.json (declared "discovery_only") into a real, working
capability: it is a scout for AION's own title/format decisions, never a
fact source for episode claims -- brain/research_planner.py's evidence
selection already cannot pick a "discovery_only" source to satisfy an
evidence requirement, so this module is intentionally kept out of that path.

Owner-requested, 2026-09-26, after reviewing Kurzgesagt, "ไอ้ก้าง เล่าเรื่อง",
"สติ๊กแมนผู้รอบรู้" and "Pure Logic" by hand: this is the repeatable version
of that same review, so it can be re-run instead of redone manually.
"""

from datetime import datetime, timezone

from tools.youtube_discovery import get_youtube_video_statistics, search_youtube_videos

DEFAULT_NICHE_QUERIES = (
    "science shorts explained",
    "history mystery shorts",
    "curiosity facts shorts",
    "why does this happen shorts",
)


def scan_niche(queries=None, videos_per_query=5, api_key=None):
    """Search AION's content niche and attach each hit's public view count.

    Returns a list of {"query", "video_id", "title", "channel", "url",
    "published_at", "view_count"} dicts, highest-viewed first. Raises
    whatever tools.youtube_discovery raises (missing API key, HTTP failure)
    -- the caller decides how to degrade.
    """
    queries = [str(item).strip() for item in (queries or DEFAULT_NICHE_QUERIES) if str(item).strip()]
    results = []
    for query in queries:
        hits = search_youtube_videos(query, limit=videos_per_query, api_key=api_key)
        video_ids = [hit["video_id"] for hit in hits]
        stats_by_id = {
            item["video_id"]: item
            for item in get_youtube_video_statistics(video_ids, api_key=api_key)
        }
        for hit in hits:
            stats = stats_by_id.get(hit["video_id"], {})
            results.append({
                "query": query,
                "video_id": hit["video_id"],
                "title": hit["title"],
                "channel": hit["channel"],
                "url": hit["url"],
                "published_at": hit["published_at"],
                "view_count": int(stats.get("view_count") or 0),
            })
    results.sort(key=lambda item: item["view_count"], reverse=True)
    return results


def scan_report(queries=None, videos_per_query=5, api_key=None):
    """A timestamped snapshot of scan_niche(), safe to persist or print.

    Never raises: a provider/network failure becomes {"ok": False, "error"}
    so a caller (CLI, dashboard, scheduled job) can show a truthful failure
    instead of crashing or inventing data.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        results = scan_niche(queries=queries, videos_per_query=videos_per_query, api_key=api_key)
        return {"generated_at": generated_at, "ok": True, "results": results}
    except Exception as exc:
        return {
            "generated_at": generated_at, "ok": False,
            "error": str(exc).strip() or type(exc).__name__, "results": [],
        }


if __name__ == "__main__":
    import json
    print(json.dumps(scan_report(), ensure_ascii=False, indent=2))
