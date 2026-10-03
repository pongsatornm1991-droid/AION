"""Read-only Facebook Page and post metrics for AION's feedback loop.

Mirrors tools/instagram_insights.py. Nothing here publishes, edits or deletes:
it only reads follower/fan counts and each recent post's reaction, comment and
share counters, using the same page token and page id the publishing tools
already use (FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID).

Reaction and comment counts need the page-engagement read permission; when the
token lacks it Meta answers with an error that surfaces as a failed capture
instead of silently recording zeros.
"""

from tools.facebook import GRAPH_API_BASE, _graph_error, _resolve_page_credentials


def _get_json(url, params):
    import requests

    response = requests.get(url, params=params, timeout=20)
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)
    return payload


def get_page_overview(page_id=None, access_token=None):
    """Return the Page's public size counters."""
    access_token, page_id = _resolve_page_credentials(access_token, page_id)
    payload = _get_json(
        f"{GRAPH_API_BASE}/{page_id}",
        {"fields": "name,fan_count,followers_count", "access_token": access_token},
    )
    return {
        "name": payload.get("name"),
        "fan_count": payload.get("fan_count"),
        "followers_count": payload.get("followers_count"),
    }


def _summary_total(item, field):
    return int(((item.get(field) or {}).get("summary") or {}).get("total_count") or 0)


def get_recent_posts(limit=10, page_id=None, access_token=None):
    """Return the Page's recent posts with their basic engagement counters."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    access_token, page_id = _resolve_page_credentials(access_token, page_id)
    payload = _get_json(
        f"{GRAPH_API_BASE}/{page_id}/posts",
        {
            "fields": (
                "id,message,created_time,permalink_url,shares,"
                "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)"
            ),
            "limit": limit,
            "access_token": access_token,
        },
    )
    return [
        {
            "id": item.get("id"),
            "message": item.get("message", ""),
            "created_time": item.get("created_time"),
            "permalink_url": item.get("permalink_url"),
            "reactions": _summary_total(item, "reactions"),
            "comments": _summary_total(item, "comments"),
            "shares": int((item.get("shares") or {}).get("count") or 0),
        }
        for item in payload.get("data", [])
    ]
