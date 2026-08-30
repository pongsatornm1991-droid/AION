"""Facebook Graph API wrapper -- the one real external-tool
implementation Phase 10 ("External integration") introduces.

Kept separate from brain/tools.py (the lifecycle machinery: action
levels, kill switch, budgets, scheduling) since this module is the one
place in the whole codebase that actually reaches the outside world;
brain/tools.py itself stays pure and network-free.

Credentials are never hardcoded and never committed: both the page
access token and the page id are read from environment variables
(FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID), loaded via .env exactly
like GEMINI_API_KEY/ANTHROPIC_API_KEY elsewhere in this project.
`requests` is imported lazily, matching the anthropic SDK's lazy-import
pattern in providers/claude.py, so importing this module never fails
for anyone not using Facebook integration and `pip install requests`
is only needed when this function actually runs.
"""

import os

from dotenv import load_dotenv

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def post_to_facebook_page(message, access_token=None, page_id=None):
    """Publish one text post to a Facebook Page's feed.

    Returns the Graph API's own response dict (contains the new
    post's id) on success. Raises RuntimeError with the Graph API's
    own error message on failure -- never retries internally, since a
    failure here is meant to be captured by
    ToolLifecycle.execute() as a "failed" action for the audit trail,
    not silently retried or swallowed.
    """

    message = str(message).strip()

    if not message:
        raise ValueError("message cannot be empty.")

    load_dotenv()

    access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")

    if not access_token:
        raise RuntimeError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured. Add it to "
            "the .env file (see .env.example)."
        )

    if not page_id:
        raise RuntimeError(
            "FACEBOOK_PAGE_ID is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{page_id}/feed"

    response = requests.post(
        url,
        data={"message": message, "access_token": access_token},
        timeout=15,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        error = payload.get("error", {})
        raise RuntimeError(
            "Facebook Graph API error "
            f"({error.get('type', 'unknown')}, code "
            f"{error.get('code', 'unknown')}): "
            f"{error.get('message') or f'HTTP {response.status_code}'}"
        )

    return payload


def _graph_error(payload, status_code):
    error = payload.get("error", {})
    return RuntimeError(
        "Facebook Graph API error "
        f"({error.get('type', 'unknown')}, code "
        f"{error.get('code', 'unknown')}): "
        f"{error.get('message') or f'HTTP {status_code}'}"
    )


def get_recent_comments(
    post_limit=5, comment_limit=25, access_token=None, page_id=None,
):
    """Fetch recent top-level comments on the Page's most recent
    posts -- the read half of Phase 11a ("two-way engagement":
    comments).

    Returns a list of dicts: {"id", "message", "post_id", "from_id",
    "from_name", "created_time"}, most recent post first. Comments
    authored by the Page itself (echoes of AION's own past replies)
    are still included here -- filtering those out is the caller's
    job (CommentAutoReplyCycle.pick_next_comment()), since this
    function's only job is a faithful, unopinionated read of the
    Graph API. Never retries internally, same discipline as
    post_to_facebook_page.
    """

    load_dotenv()

    access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")

    if not access_token:
        raise RuntimeError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured. Add it to "
            "the .env file (see .env.example)."
        )

    if not page_id:
        raise RuntimeError(
            "FACEBOOK_PAGE_ID is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{page_id}/feed"
    params = {
        "fields": f"comments.limit({comment_limit}){{id,message,from,created_time}}",
        "limit": post_limit,
        "access_token": access_token,
    }

    response = requests.get(url, params=params, timeout=15)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    comments = []

    for post in payload.get("data", []):
        post_id = post.get("id")
        post_comments = (post.get("comments") or {}).get("data", [])

        for entry in post_comments:
            from_field = entry.get("from") or {}
            comments.append({
                "id": entry.get("id"),
                "message": entry.get("message", ""),
                "post_id": post_id,
                "from_id": from_field.get("id"),
                "from_name": from_field.get("name"),
                "created_time": entry.get("created_time"),
            })

    return comments


def reply_to_facebook_comment(comment_id, message, access_token=None):
    """Publish one reply to an existing Facebook comment -- the write
    half of Phase 11a.

    Returns the Graph API's own response dict (contains the new
    reply's id) on success. Raises RuntimeError on failure -- never
    retries internally, since a failure here is meant to be captured
    by ToolLifecycle.execute() as a "failed" action for the audit
    trail, exactly like post_to_facebook_page.
    """

    message = str(message).strip()

    if not message:
        raise ValueError("message cannot be empty.")

    if not comment_id:
        raise ValueError("comment_id cannot be empty.")

    load_dotenv()

    access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

    if not access_token:
        raise RuntimeError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured. Add it to "
            "the .env file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{comment_id}/comments"

    response = requests.post(
        url,
        data={"message": message, "access_token": access_token},
        timeout=15,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return payload
