"""Publish completed AION Reels to YouTube exactly once.

YouTube is intentionally downstream of the existing Reel lifecycle: an idea
must already have passed AION's social safety gate and been recorded as a
published Reel before it can become a Short.
"""

import json
import os


class YouTubeShortsCycle:
    PUBLISHED = "published_reels"

    def __init__(self, memory, uploader=None):
        self.memory = memory
        self.uploader = uploader

    def _next_reel(self):
        entries = self.memory.all(self.PUBLISHED)
        for entry in sorted(entries, key=lambda item: item.get("timestamp", "")):
            try:
                payload = json.loads(entry["content"])
            except (TypeError, ValueError):
                continue
            if not (payload.get("youtube") or {}).get("video_id"):
                return entry, payload
        return None, None

    @staticmethod
    def _title(caption):
        first_line = next((line.strip() for line in str(caption).splitlines() if line.strip()), "AION is learning")
        return first_line[:100]

    def publish_once(self, repo_root=None):
        entry, payload = self._next_reel()
        if entry is None:
            return {"stage": "no-pending"}

        video_path = payload.get("video_path")
        if not video_path:
            return {"stage": "missing-video", "entry_id": entry.get("id")}
        root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        absolute_video_path = os.path.join(root, video_path)
        caption = str(payload.get("caption", "")).strip()
        from brain.cross_platform import append_invitation
        description = "\n\n".join(
            part for part in (
                append_invitation(caption, "youtube", self.memory),
                "#Shorts #AION #AI",
            ) if part
        )
        try:
            if self.uploader is None:
                from tools.youtube import upload_short
                uploader = upload_short
            else:
                uploader = self.uploader
            result = uploader(absolute_video_path, self._title(caption), description)
        except Exception as exc:
            return {"stage": "upload-failed", "error": str(exc), "entry_id": entry.get("id")}

        payload["youtube"] = result
        self.memory.update(self.PUBLISHED, entry["id"], content=json.dumps(payload, ensure_ascii=False))
        self.memory.remember(
            category="social_language_log",
            content=f"platform=youtube-short; language={payload.get('language', 'en')}; video={result.get('video_id', 'unknown')}",
            memory_type="action", source="aion-youtube-publish", importance=1,
            tags=["youtube", "shorts", payload.get("language", "en")],
        )
        return {"stage": "published", "caption": caption, **result}
