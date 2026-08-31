"""Read-only Instagram account and media metrics for AION's feedback loop."""

from tools.facebook import GRAPH_API_BASE, _graph_error
from tools.instagram import _resolve_credentials


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


def get_account_overview(account_id=None, access_token=None):
    """Return the basic public performance counters for the owned account."""
    access_token, account_id = _resolve_credentials(access_token, account_id)
    payload = _get_json(
        f"{GRAPH_API_BASE}/{account_id}",
        {
            "fields": "username,followers_count,media_count",
            "access_token": access_token,
        },
    )
    return {
        "username": payload.get("username"),
        "followers_count": payload.get("followers_count"),
        "media_count": payload.get("media_count"),
    }


def get_recent_media(limit=10, account_id=None, access_token=None):
    """Return recent posts and their basic engagement counters.

    Likes and comments are intentionally used as the baseline because they are
    broadly available to professional accounts. More granular Insights metrics
    can be added later without making this feedback loop depend on them.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    access_token, account_id = _resolve_credentials(access_token, account_id)
    payload = _get_json(
        f"{GRAPH_API_BASE}/{account_id}/media",
        {
            "fields": "id,caption,timestamp,like_count,comments_count,media_type,permalink",
            "limit": limit,
            "access_token": access_token,
        },
    )
    return [
        {
            "id": item.get("id"),
            "caption": item.get("caption", ""),
            "timestamp": item.get("timestamp"),
            "like_count": item.get("like_count", 0),
            "comments_count": item.get("comments_count", 0),
            "media_type": item.get("media_type"),
            "permalink": item.get("permalink"),
        }
        for item in payload.get("data", [])
        if item.get("id")
    ]
