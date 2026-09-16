"""Cross-post one finished Creator Studio Short without using an older Reel.

The regular social queue may contain unrelated posts.  This bridge is for a
named Studio episode that already passed the same local video-quality gate as
YouTube, so a promised cross-platform release cannot silently substitute a
historical asset.
"""

import json
import os

from brain.creator_series import CreatorSeriesRegistry
from brain.identity_disclosure import append_identity_disclosure
from brain.video_quality import VideoQualityGate


class CreatorEpisodeCrosspost:
    CATEGORY = "creator_episode_crossposts"

    def __init__(self, memory, root):
        self.memory = memory
        self.root = root

    def _record(self, episode_id):
        for entry in self.memory.all(self.CATEGORY):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if payload.get("episode_id") == episode_id:
                return entry, payload
        return None, None

    def publish_once(self, episode_id, instagram_publisher=None, facebook_publisher=None):
        episode = next((item for item in CreatorSeriesRegistry(self.root).episodes()
                        if item.get("id") == episode_id), None)
        if not episode:
            return {"stage": "unknown-creator-episode"}
        if episode.get("format") != "illustrated-narrated-short":
            return {"stage": "not-a-short"}
        video_path = self.root / "content" / "reels" / f"{episode_id}.mp4"
        quality = VideoQualityGate(self.root).assess(video_path, "short")
        if not quality.get("eligible"):
            return {"stage": "quality-gate-blocked", "quality": quality}
        repo = os.getenv("GITHUB_REPOSITORY")
        if not repo:
            return {"stage": "missing-github-repository"}
        url = f"https://raw.githubusercontent.com/{repo}/main/content/reels/{episode_id}.mp4"
        caption = "\n\n".join((
            str(episode.get("title") or "AION Wonders"),
            str(episode.get("audience_promise") or ""),
            str(episode.get("uncertainty_boundary") or ""),
        )).strip()
        entry, record = self._record(episode_id)
        record = record or {"episode_id": episode_id, "video_url": url, "platforms": {}}
        platforms = dict(record.get("platforms") or {})
        if entry is None:
            entry = self.memory.remember(
                self.CATEGORY, json.dumps(record, ensure_ascii=False), memory_type="action",
                source="aion-creator-episode-crosspost", importance=3,
                tags=["creator", "crosspost", episode_id],
            )

        if not platforms.get("instagram"):
            try:
                if instagram_publisher is None:
                    from tools.instagram import publish_video
                    instagram_publisher = publish_video
                result = instagram_publisher(url, caption=append_identity_disclosure(caption, "instagram"))
                platforms["instagram"] = {"status": "published", "result": result}
            except Exception as exc:
                platforms["instagram"] = {"status": "failed", "error": str(exc)}
        record["platforms"] = platforms
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(record, ensure_ascii=False))

        if not platforms.get("facebook"):
            try:
                if facebook_publisher is None:
                    from tools.facebook import publish_reel_to_facebook
                    facebook_publisher = publish_reel_to_facebook
                result = facebook_publisher(url, caption=append_identity_disclosure(caption, "facebook"))
                platforms["facebook"] = {"status": "published", "result": result}
            except Exception as exc:
                platforms["facebook"] = {"status": "failed", "error": str(exc)}
        record["platforms"] = platforms
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(record, ensure_ascii=False))
        complete = all(platforms.get(name, {}).get("status") == "published" for name in ("instagram", "facebook"))
        return {"stage": "published" if complete else "partially-published", "episode_id": episode_id,
                "video_url": url, "platforms": platforms}

    def publish_latest_once(self, instagram_publisher=None, facebook_publisher=None):
        """Find the newest public Studio Short missing a social delivery.

        This is deliberately based on the durable YouTube audit trail rather
        than a filename or modification date.  Thus an automatic retry cannot
        accidentally select an unreviewed storyboard or an older local Reel.
        """
        for entry in reversed(self.memory.all("youtube_creator_queue")):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            episode_id = str(payload.get("episode_id") or "")
            youtube = payload.get("youtube") or {}
            if payload.get("content_kind") != "short" or not episode_id:
                continue
            if not youtube.get("video_id") or youtube.get("privacy_status") != "public":
                continue
            # A historical YouTube record is not enough. Re-check the exact
            # local episode before delivery so an old 27-second render can
            # never occupy a new Facebook/Instagram slot.
            video_path = self.root / "content" / "reels" / f"{episode_id}.mp4"
            if not VideoQualityGate(self.root).assess(video_path, "short").get("eligible"):
                continue
            _, crosspost = self._record(episode_id)
            platforms = (crosspost or {}).get("platforms") or {}
            if all(platforms.get(name, {}).get("status") == "published" for name in ("instagram", "facebook")):
                continue
            return self.publish_once(episode_id, instagram_publisher, facebook_publisher)
        return {"stage": "no-public-creator-short-awaiting-crosspost"}
