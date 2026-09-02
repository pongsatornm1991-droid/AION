"""Read-only YouTube discovery for AION's learning cycle.

Only public video metadata is requested.  This adapter intentionally does not
download captions/transcripts, comments, media, or perform any account action.
"""

import os

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_youtube_videos(query, limit=3, api_key=None):
    query = str(query).strip()
    if not query:
        raise ValueError("query cannot be empty")
    api_key = api_key or os.getenv("YOUTUBE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_DATA_API_KEY is required for YouTube discovery")
    import requests
    response = requests.get(YOUTUBE_SEARCH_URL, params={
        "part": "snippet", "type": "video", "q": query,
        "maxResults": max(1, min(int(limit), 10)), "safeSearch": "strict", "key": api_key,
    }, timeout=15)
    if response.status_code >= 400:
        raise RuntimeError(f"YouTube discovery error: HTTP {response.status_code}")
    try:
        items = response.json().get("items", [])
    except ValueError as exc:
        raise RuntimeError("YouTube discovery error: invalid JSON") from exc
    results = []
    for item in items:
        video_id = ((item.get("id") or {}).get("videoId") or "").strip()
        snippet = item.get("snippet") or {}
        if not video_id or not snippet.get("title"):
            continue
        results.append({
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": str(snippet.get("title") or "")[:240],
            "channel": str(snippet.get("channelTitle") or "")[:160],
            "published_at": snippet.get("publishedAt"),
            "description": str(snippet.get("description") or "")[:800],
        })
    return results
