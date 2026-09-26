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


def upload_short(video_path, title, description, privacy_status=None, thumbnail_path=None, tags=None):
    """Upload one local vertical video and return only safe public metadata."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"YouTube video file was not found: {path}")
    if path.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
        raise ValueError("YouTube upload must be a video file (.mp4, .mov, or .m4v)")
    thumbnail = Path(thumbnail_path) if thumbnail_path else None
    if thumbnail is not None and (not thumbnail.is_file() or thumbnail.suffix.lower() not in {".png", ".jpg", ".jpeg"}):
        raise ValueError("YouTube thumbnail must be an existing PNG or JPEG image")

    status = (privacy_status or os.getenv("YOUTUBE_PRIVACY_STATUS", "private")).strip().lower()
    if status not in VALID_PRIVACY:
        raise ValueError("YOUTUBE_PRIVACY_STATUS must be private, unlisted, or public")

    snippet = {
        "title": str(title).strip()[:100] or "AION is learning",
        "description": str(description).strip()[:5000],
        "categoryId": "28",  # Science & Technology
    }
    if tags:
        # YouTube caps the combined tags string at 500 characters; trim from
        # the end (least-specific tags go last, see YouTubeCreatorQueue's
        # tag builder) rather than reject the whole list over one long entry.
        kept, budget = [], 500
        for tag in tags:
            tag = str(tag).strip()
            if not tag or len(tag) > budget:
                continue
            kept.append(tag)
            budget -= len(tag) + 1  # YouTube joins tags with a comma
        if kept:
            snippet["tags"] = kept

    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_UPLOAD_SCOPE]), cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": snippet,
            "status": {"privacyStatus": status, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    result = {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": response.get("status", {}).get("privacyStatus", status),
    }
    if thumbnail is not None:
        try:
            thumbnail_request = youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail), mimetype="image/png", resumable=True),
            )
            thumbnail_response = None
            while thumbnail_response is None:
                _, thumbnail_response = thumbnail_request.next_chunk()
            result["thumbnail_status"] = "set"
        except Exception as exc:
            # The video is already created when this optional provider action
            # happens. Keep its durable id so a retry never uploads a second
            # copy. The dashboard can then show the exact owner-side account
            # capability still needed for a custom thumbnail.
            result["thumbnail_status"] = "provider-permission-required"
            result["thumbnail_error"] = str(exc).strip() or type(exc).__name__
    return result


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
    # Visibility changes, like comment replies, require the channel-management
    # consent scope. Upload-only tokens can create a private upload but cannot
    # safely change its public visibility afterwards.
    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    response = youtube.videos().update(
        part="status",
        body={"id": identifier, "status": {"privacyStatus": status, "selfDeclaredMadeForKids": False}},
    ).execute()
    return {
        "video_id": identifier,
        "url": f"https://www.youtube.com/watch?v={identifier}",
        "privacy_status": (response.get("status") or {}).get("privacyStatus", status),
    }


def get_video_snippet(video_id):
    """Read a video's current live title/description (e.g. before translating
    them). Read-only; never used to infer anything beyond what's returned."""
    from googleapiclient.discovery import build

    identifier = str(video_id or "").strip()
    if not identifier:
        raise ValueError("A YouTube video id is required")
    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    response = youtube.videos().list(part="snippet", id=identifier).execute()
    items = response.get("items") or []
    if not items:
        raise RuntimeError(f"No YouTube video found for id {identifier}")
    snippet = items[0]["snippet"]
    return {"title": snippet.get("title") or "", "description": snippet.get("description") or ""}


def update_video_description(video_id, description):
    """Replace an existing upload's own (primary-language) description.

    Read-modify-write, like set_video_localization: the API replaces the
    whole snippet it's given, not a partial patch, so the current snippet
    is read first and only `description` is changed -- title, tags, and
    category are preserved exactly as they were.
    """
    from googleapiclient.discovery import build

    identifier = str(video_id or "").strip()
    if not identifier:
        raise ValueError("A YouTube video id is required")
    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    current = youtube.videos().list(part="snippet", id=identifier).execute()
    items = current.get("items") or []
    if not items:
        raise RuntimeError(f"No YouTube video found for id {identifier}")
    snippet = items[0]["snippet"]
    snippet["description"] = str(description).strip()[:5000]
    response = youtube.videos().update(part="snippet", body={"id": identifier, "snippet": snippet}).execute()
    return {"video_id": identifier, "description": response.get("snippet", {}).get("description", "")}


def set_video_localization(video_id, language_code, title, description):
    """Add or replace one language's localized title/description for an
    existing upload, without touching audio, captions, thumbnail, or any
    other setting -- this is the same "localizations" field YouTube Studio's
    own per-video Language tab writes to (verified against the owner's own
    Studio screenshots, 2026-09-27: title/description translations there are
    a distinct, older, fully API-backed feature from multi-language audio
    dubbing, which as of this writing has no confirmed public Data API
    endpoint and also gates on the channel having "Advanced features").

    YouTube's `update` call replaces the entire `snippet` it's given, not a
    partial patch, so the current snippet is read first and only
    `localizations` is changed -- this cannot silently drop the video's
    existing title, tags, or category the way a naive partial body would.
    """
    from googleapiclient.discovery import build

    identifier = str(video_id or "").strip()
    if not identifier:
        raise ValueError("A YouTube video id is required")
    language_code = str(language_code or "").strip().lower()
    if not language_code:
        raise ValueError("A BCP-47/ISO 639-1 language code is required")

    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    current = youtube.videos().list(part="snippet,localizations", id=identifier).execute()
    items = current.get("items") or []
    if not items:
        raise RuntimeError(f"No YouTube video found for id {identifier}")

    snippet = items[0]["snippet"]
    # Localizations are rejected outright unless the video already declares
    # what language its own snippet.title/description are written in.
    if not snippet.get("defaultLanguage"):
        snippet["defaultLanguage"] = "en"
    localizations = dict(items[0].get("localizations") or {})
    localizations[language_code] = {
        "title": str(title).strip()[:100],
        "description": str(description).strip()[:5000],
    }
    response = youtube.videos().update(
        part="snippet,localizations",
        body={"id": identifier, "snippet": snippet, "localizations": localizations},
    ).execute()
    return {"video_id": identifier, "language": language_code, "localizations": response.get("localizations", {})}


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


def list_uploaded_videos(limit=200):
    """List every video already on the channel: id, title, privacy, publish time.

    Read-only drift-detection helper. Deliberately reuses YOUTUBE_COMMENT_SCOPE
    (already granted for comment moderation / set_video_privacy) rather than
    asking for a new OAuth scope and a fresh owner consent just to list videos.
    Includes private and unlisted uploads, not only public ones, because the
    owner's own "uploads" playlist returns all of them -- this is deliberate:
    an already-public video with no Studio queue record is a duplicate-upload
    risk, but a video that silently stayed private after a swallowed publish
    error is worth surfacing too.
    """
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=youtube_credentials([YOUTUBE_COMMENT_SCOPE]), cache_discovery=False)
    channels = youtube.channels().list(part="contentDetails", mine=True).execute()
    items = channels.get("items") or []
    if not items:
        return []
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    entries = []
    page_token = None
    while len(entries) < limit:
        response = youtube.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=uploads_playlist_id,
            maxResults=min(50, limit - len(entries)),
            pageToken=page_token,
        ).execute()
        for item in response.get("items", []):
            content = item.get("contentDetails") or {}
            snippet = item.get("snippet") or {}
            video_id = content.get("videoId")
            if video_id:
                entries.append({
                    "video_id": video_id,
                    "title": snippet.get("title"),
                    "published_at": content.get("videoPublishedAt"),
                })
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    # A second, batched call for privacyStatus: playlistItems never carries
    # it, and videos.list accepts at most 50 ids per call.
    privacy_by_id = {}
    ids = [entry["video_id"] for entry in entries]
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        response = youtube.videos().list(part="status", id=",".join(batch)).execute()
        for item in response.get("items", []):
            privacy_by_id[item.get("id")] = (item.get("status") or {}).get("privacyStatus")

    for entry in entries:
        entry["privacy_status"] = privacy_by_id.get(entry["video_id"])
    return entries
