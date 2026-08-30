"""Instagram Graph API wrapper -- the Instagram counterpart to
tools/facebook.py, added when AION expanded from Facebook-only to a
second platform (2026-08-30, "Aion i Robot" / @aion_i.robot).

Uses the same underlying Graph API as tools/facebook.py (Instagram
publishing is exposed through Meta's Graph API once an Instagram
professional account is linked to a Facebook Page -- see
docs/GITHUB_ACTIONS_SETUP.md for the linking steps), so this module
reuses tools.facebook's GRAPH_API_BASE and _graph_error rather than
duplicating the version pin and error-formatting logic.

Credentials are never hardcoded and never committed: both the access
token and the Instagram Business Account ID are read from environment
variables (INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID),
loaded via .env exactly like the Facebook/Gemini/Telegram credentials
elsewhere in this project. `requests` is imported lazily, matching
tools/facebook.py's pattern, so importing this module never fails for
anyone not using Instagram integration.

Instagram's Content Publishing API is a two-step "container" flow,
unlike Facebook's single-call post:
  1. Create a media container (POST .../media) with an image_url or
     video_url the Instagram servers fetch content from directly --
     Instagram does not accept a raw file upload, only a URL it can
     reach. AION's video/image pipeline is expected to publish its
     rendered file somewhere public (e.g. a public GitHub repo path
     via raw.githubusercontent.com) and pass that URL in here.
  2. Publish that container (POST .../media_publish) once it is
     ready. Photo containers are usually ready immediately; video/
     Reels containers need time to process on Instagram's side, so
     publish_video() polls the container's status_code until it
     reports FINISHED (or ERROR/timeout) before publishing.

Every function here never retries internally, matching
tools/facebook.py's discipline -- a failure here is meant to be
captured by ToolLifecycle.execute() as a "failed" action for the
audit trail, not silently retried or swallowed.
"""

import os
import time

from dotenv import load_dotenv

from tools.facebook import GRAPH_API_BASE, _graph_error


def _resolve_credentials(access_token, account_id):
    load_dotenv()

    access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if not access_token:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN is not configured. Add it to the "
            ".env file (see .env.example)."
        )

    if not account_id:
        raise RuntimeError(
            "INSTAGRAM_BUSINESS_ACCOUNT_ID is not configured. Add it "
            "to the .env file (see .env.example)."
        )

    return access_token, account_id


def create_media_container(
    image_url=None,
    video_url=None,
    caption="",
    is_reel=False,
    account_id=None,
    access_token=None,
):
    """Create an Instagram media container from a publicly reachable
    image or video URL -- step 1 of the two-step publish flow.

    Exactly one of image_url/video_url must be given. Returns the
    Graph API's own response dict (contains the new container's id
    under "id") on success. Raises RuntimeError with the Graph API's
    own error message on failure.
    """

    if bool(image_url) == bool(video_url):
        raise ValueError(
            "Provide exactly one of image_url or video_url, not both "
            "or neither."
        )

    access_token, account_id = _resolve_credentials(access_token, account_id)

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{account_id}/media"
    data = {"caption": str(caption or ""), "access_token": access_token}

    if image_url:
        data["image_url"] = image_url
    else:
        data["video_url"] = video_url
        data["media_type"] = "REELS" if is_reel else "VIDEO"

    response = requests.post(url, data=data, timeout=30)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return payload


def get_container_status(container_id, access_token=None):
    """Read a media container's processing status.

    Returns a dict: {"status_code": one of "EXPIRED"/"ERROR"/
    "FINISHED"/"IN_PROGRESS"/"PUBLISHED", "status": a human-readable
    detail string}. Photo containers are typically already FINISHED
    the moment they're created; video/Reels containers start
    IN_PROGRESS and need polling (see wait_for_container_ready).
    """

    if not container_id:
        raise ValueError("container_id cannot be empty.")

    load_dotenv()

    access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")

    if not access_token:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN is not configured. Add it to the "
            ".env file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{container_id}"
    params = {"fields": "status_code,status", "access_token": access_token}

    response = requests.get(url, params=params, timeout=15)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return {
        "status_code": payload.get("status_code"),
        "status": payload.get("status"),
    }


def wait_for_container_ready(
    container_id, access_token=None, max_attempts=30, poll_interval=10,
):
    """Poll a video/Reels container until Instagram finishes
    processing it, or raise.

    Raises RuntimeError if the container reports ERROR/EXPIRED, or if
    it is still not FINISHED after max_attempts polls -- callers
    (publish_video) treat either as a failed publish, same as any
    other Graph API error, rather than retrying indefinitely.
    """

    for _ in range(max_attempts):
        status = get_container_status(container_id, access_token=access_token)
        code = status.get("status_code")

        if code == "FINISHED":
            return status

        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(
                f"Instagram media container {container_id} failed to "
                f"process (status_code={code}): "
                f"{status.get('status') or 'no further detail given'}"
            )

        time.sleep(poll_interval)

    raise RuntimeError(
        f"Instagram media container {container_id} did not finish "
        f"processing within {max_attempts * poll_interval} seconds."
    )


def publish_container(creation_id, account_id=None, access_token=None):
    """Publish an already-created, ready media container -- step 2 of
    the two-step publish flow.

    Returns the Graph API's own response dict (contains the newly
    published media's id) on success. Raises RuntimeError on failure.
    """

    if not creation_id:
        raise ValueError("creation_id cannot be empty.")

    access_token, account_id = _resolve_credentials(access_token, account_id)

    import requests  # lazy: only needed when this actually runs

    url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
    data = {"creation_id": creation_id, "access_token": access_token}

    response = requests.post(url, data=data, timeout=30)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    return payload


def publish_photo(image_url, caption="", account_id=None, access_token=None):
    """Publish a single photo to Instagram in one call -- the common
    case, since photo containers are ready to publish immediately
    (no polling needed).

    Returns the published media's Graph API response dict. Raises
    RuntimeError on failure at either the container-creation or
    publish step.
    """

    if not image_url:
        raise ValueError("image_url cannot be empty.")

    container = create_media_container(
        image_url=image_url,
        caption=caption,
        account_id=account_id,
        access_token=access_token,
    )

    return publish_container(
        container["id"], account_id=account_id, access_token=access_token,
    )


def publish_video(
    video_url,
    caption="",
    is_reel=True,
    account_id=None,
    access_token=None,
    max_attempts=30,
    poll_interval=10,
):
    """Publish a video (Reel by default) to Instagram: create the
    container, wait for Instagram to finish processing it, then
    publish it.

    Returns the published media's Graph API response dict. Raises
    RuntimeError on failure at the container-creation, processing, or
    publish step -- never retries the whole flow internally, matching
    every other write in this module.
    """

    if not video_url:
        raise ValueError("video_url cannot be empty.")

    container = create_media_container(
        video_url=video_url,
        caption=caption,
        is_reel=is_reel,
        account_id=account_id,
        access_token=access_token,
    )

    wait_for_container_ready(
        container["id"],
        access_token=access_token,
        max_attempts=max_attempts,
        poll_interval=poll_interval,
    )

    return publish_container(
        container["id"], account_id=account_id, access_token=access_token,
    )
