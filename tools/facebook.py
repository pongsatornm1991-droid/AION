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


def _resolve_page_credentials(access_token=None, page_id=None):
    load_dotenv()
    access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")
    if not access_token:
        raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is not configured. Add it to the .env file (see .env.example).")
    if not page_id:
        raise RuntimeError("FACEBOOK_PAGE_ID is not configured. Add it to the .env file (see .env.example).")
    return access_token, page_id


def publish_reel_to_facebook(video_url, caption="", access_token=None, page_id=None):
    """Publish a public MP4 as a Facebook Page Reel.

    The Reels API requires a three-stage transfer: start an upload session,
    stream the public video to Meta's upload URL, then finish as PUBLISHED.
    It deliberately performs no whole-operation retry; ReelContentCycle
    checkpoints each platform after success and retries only the unfinished
    platform on a later scheduled run.
    """
    video_url = str(video_url or "").strip()
    if not video_url:
        raise ValueError("video_url cannot be empty.")
    access_token, page_id = _resolve_page_credentials(access_token, page_id)
    import requests

    endpoint = f"{GRAPH_API_BASE}/{page_id}/video_reels"
    # The Page Reels endpoint expects form fields, not a JSON body.  Sending
    # JSON can yield an opaque HTTP 400 before Meta even creates an upload
    # session, despite the same token working for ordinary Page posts.
    start = requests.post(
        endpoint, data={"upload_phase": "start", "access_token": access_token}, timeout=30,
    )
    try:
        start_payload = start.json()
    except ValueError:
        start_payload = {}
    if start.status_code >= 400 or "error" in start_payload:
        raise _graph_error(start_payload, start.status_code, getattr(start, "text", ""))
    video_id, upload_url = start_payload.get("video_id"), start_payload.get("upload_url")
    if not video_id or not upload_url:
        raise RuntimeError("Facebook Reels API did not return video_id and upload_url.")

    source = requests.get(video_url, stream=True, timeout=90)
    if source.status_code >= 400:
        raise RuntimeError(f"Could not download the rendered Reel for Facebook (HTTP {source.status_code}).")
    # Meta's resumable-upload host validates the byte length twice.  Passing
    # an iterator makes requests use chunked transfer encoding, which the
    # host rejects unless it receives the matching entity-length headers.
    # Reels produced by AION are intentionally short, so materialising this
    # one bounded asset makes the transfer deterministic and inspectable.
    video_bytes = b"".join(source.iter_content(chunk_size=1024 * 1024))
    file_size = str(len(video_bytes))
    if not video_bytes:
        raise RuntimeError("The rendered Reel download was empty.")
    upload = requests.post(
        upload_url,
        data=video_bytes,
        headers={
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": file_size,
            "Content-Length": file_size,
            "X-Entity-Length": file_size,
            "Content-Type": "application/octet-stream",
        },
        timeout=180,
    )
    try:
        upload_payload = upload.json()
    except ValueError:
        upload_payload = {}
    if upload.status_code >= 400 or "error" in upload_payload:
        raise _graph_error(upload_payload, upload.status_code, getattr(upload, "text", ""))

    finish = requests.post(
        endpoint,
        data={"upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED", "description": str(caption or ""), "access_token": access_token},
        timeout=30,
    )
    try:
        finish_payload = finish.json()
    except ValueError:
        finish_payload = {}
    if finish.status_code >= 400 or "error" in finish_payload:
        raise _graph_error(finish_payload, finish.status_code, getattr(finish, "text", ""))
    return finish_payload


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


def post_photo_to_facebook(image_url, caption="", access_token=None, page_id=None):
    """Publish one photo to a Facebook Page's feed, given a public
    image URL (Facebook fetches the file itself, no raw upload --
    the same one-step shape tools/instagram.py's photo container flow
    aims at, simpler here since a Facebook Page photo post needs no
    separate publish step the way an Instagram media container does).

    Built 2026-09-03 so VisualContentCycle can cross-post the exact
    same rendered image + caption that already goes to Instagram to
    the Facebook Page too, instead of only Instagram -- mirrors
    ReelContentCycle's own existing per-platform checkpoint loop in
    brain/reels.py (publish_reel_to_facebook is that same pattern's
    video counterpart).

    Returns the Graph API's own response dict (contains the new
    post's id) on success. Raises RuntimeError with the Graph API's
    own error message on failure -- never retries internally, same
    discipline as post_to_facebook_page() above.
    """

    image_url = str(image_url or "").strip()

    if not image_url:
        raise ValueError("image_url cannot be empty.")

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

    url = f"{GRAPH_API_BASE}/{page_id}/photos"

    response = requests.post(
        url,
        data={
            "url": image_url,
            "caption": str(caption or ""),
            "access_token": access_token,
        },
        timeout=30,
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


def _graph_error(payload, status_code, response_text=""):
    error = payload.get("error", {})
    detail = error.get("message") or str(response_text or "").strip()
    return RuntimeError(
        "Facebook Graph API error "
        f"({error.get('type', 'unknown')}, code "
        f"{error.get('code', 'unknown')}): "
        f"{detail or f'HTTP {status_code}'}"
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


def get_page_bio(page_id=None, access_token=None):
    """Read AION's configured Facebook Page's current "about" text --
    the read half of Phase 12 ("identity change approval").

    Returns the current bio as a plain string (empty string if the
    Page has none set). Never retries internally, same discipline as
    the rest of this module.
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

    url = f"{GRAPH_API_BASE}/{page_id}"
    params = {"fields": "about", "access_token": access_token}

    response = requests.get(url, params=params, timeout=15)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return payload.get("about", "")


def update_page_bio(new_bio, page_id=None, access_token=None):
    """Change AION's configured Facebook Page's "about" text -- the
    write half of Phase 12, and the only place in this codebase that
    changes how AION *presents itself* rather than what it says.

    Deliberately never called directly by any autonomous cycle: every
    call site in brain/profile_change.py goes through ToolLifecycle
    under ActionLevel.IDENTITY_CHANGE, which can never be self-
    approved by AION (see brain/tools.py's _NEVER_SELF_APPROVE) -- a
    real person must approve it, via the Telegram inline-button flow.

    Returns the Graph API's own response dict on success. Raises
    RuntimeError on failure -- never retries internally, matching
    post_to_facebook_page/reply_to_facebook_comment.
    """

    new_bio = str(new_bio).strip()

    if not new_bio:
        raise ValueError("new_bio cannot be empty.")

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

    url = f"{GRAPH_API_BASE}/{page_id}"

    response = requests.post(
        url,
        data={"about": new_bio, "access_token": access_token},
        timeout=15,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return payload


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
