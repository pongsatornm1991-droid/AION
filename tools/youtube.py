"""Small, explicit YouTube Shorts uploader for AION.

Credentials come only from environment variables so they never enter AION's
memory, source control, Telegram, or an action report.
"""

import os
from pathlib import Path


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_COMMENT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
VALID_PRIVACY = {"private", "unlisted", "public"}


def _required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for YouTube publishing")
    return value


def youtube_credentials(scopes=None):
    """Build refreshable OAuth credentials without exposing token values."""
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=_required("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_required("YOUTUBE_CLIENT_ID"),
        client_secret=_required("YOUTUBE_CLIENT_SECRET"),
        scopes=list(scopes or [YOUTUBE_UPLOAD_SCOPE]),
    )


def upload_short(video_path, title, description, privacy_status=None):
    """Upload one local vertical video and return only safe public metadata."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"YouTube video file was not found: {path}")
    if path.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
        raise ValueError("YouTube upload must be a video file (.mp4, .mov, or .m4v)")

    status = (privacy_status or os.getenv("YOUTUBE_PRIVACY_STATUS", "private")).strip().lower()
    if status not in VALID_PRIVACY:
        raise ValueError("YOUTUBE_PRIVACY_STATUS must be private, unlisted, or public")

    youtube = build("youtube", "v3", credentials=youtube_credentials(), cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": str(title).strip()[:100] or "AION is learning",
                "description": str(description).strip()[:5000],
                "categoryId": "28",  # Science & Technology
            },
            "status": {"privacyStatus": status, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": response.get("status", {}).get("privacyStatus", status),
    }


def set_video_privacy(video_id, privacy_status="public"):
    """Change visibility for an existing AION upload without exposing tokens.

    The caller is responsible for selecting only quality-gated AION records.
    This deliberately cannot alter title, description, audience settings, or
    any account configuration.
    """
    from googleapiclient.discovery import build

    status = str(privacy_status).strip().lower()
    if status not in VALID_PRIVACY:
        raise ValueError("YOUTUBE_PRIVACY_STATUS must be private, unlisted, or public")
    identifier = str(video_id or "").strip()
    if not identifier:
        raise ValueError("A YouTube video id is required")
    youtube = build("youtube", "v3", credentials=youtube_credentials(), cache_discovery=False)
    response = youtube.videos().update(
        part="status",
        body={"id": identifier, "status": {"privacyStatus": status, "selfDeclaredMadeForKids": False}},
    ).execute()
    return {
        "video_id": identifier,
        "url": f"https://www.youtube.com/watch?v={identifier}",
        "privacy_status": (response.get("status") or {}).get("privacyStatus", status),
    }


def get_recent_channel_comments(limit=20):
    """Read recent channel comments as data; never returns credentials."""
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    channel = youtube.channels().list(part="id", mine=True).execute()
    items = channel.get("items") or []
    if not items:
        return []
    response = youtube.commentThreads().list(
        part="snippet", allThreadsRelatedToChannelId=items[0]["id"], maxResults=min(max(1, int(limit)), 100), order="time",
    ).execute()
    comments = []
    for item in response.get("items") or []:
        top = ((item.get("snippet") or {}).get("topLevelComment") or {})
        snippet = top.get("snippet") or {}
        comments.append({
            "id": top.get("id"), "message": snippet.get("textDisplay") or "",
            "from_id": snippet.get("authorChannelId", {}).get("value"),
            "from_name": snippet.get("authorDisplayName"), "created_time": snippet.get("publishedAt"),
        })
    return [item for item in comments if item.get("id")]


def reply_to_youtube_comment(comment_id, message):
    """Reply once to an existing YouTube comment after AION's safety gate."""
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    response = youtube.comments().insert(part="snippet", body={
        "snippet": {"parentId": str(comment_id), "textOriginal": str(message).strip()},
    }).execute()
    return {"comment_id": response.get("id"), "parent_id": str(comment_id)}
