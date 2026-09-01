"""Small, explicit YouTube Shorts uploader for AION.

Credentials come only from environment variables so they never enter AION's
memory, source control, Telegram, or an action report.
"""

import os
from pathlib import Path


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
VALID_PRIVACY = {"private", "unlisted", "public"}


def _required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for YouTube publishing")
    return value


def youtube_credentials():
    """Build refreshable OAuth credentials without exposing token values."""
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=_required("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_required("YOUTUBE_CLIENT_ID"),
        client_secret=_required("YOUTUBE_CLIENT_SECRET"),
        scopes=[YOUTUBE_UPLOAD_SCOPE],
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
