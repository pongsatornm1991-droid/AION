"""Turn real Instagram performance changes into bounded AION memory."""

import json


class InstagramFeedbackCycle:
    """Records only changed Instagram counters, never repeated snapshots."""

    CATEGORY = "social_feedback"
    SOURCE = "instagram-feedback"

    def __init__(self, memory, overview_reader, media_reader):
        self.memory = memory
        self.overview_reader = overview_reader
        self.media_reader = media_reader

    def _latest_snapshots(self):
        snapshots = {"account": None, "media": {}}
        try:
            entries = self.memory.all(self.CATEGORY)
        except Exception:
            entries = []

        for entry in entries:
            if entry.get("source") != self.SOURCE:
                continue
            try:
                data = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if data.get("kind") == "account":
                snapshots["account"] = data
            elif data.get("kind") == "media" and data.get("media_id"):
                snapshots["media"][data["media_id"]] = data
        return snapshots

    @staticmethod
    def _account_snapshot(overview):
        return {
            "kind": "account",
            "username": overview.get("username"),
            "followers_count": overview.get("followers_count"),
            "media_count": overview.get("media_count"),
        }

    @staticmethod
    def _media_snapshot(media):
        return {
            "kind": "media",
            "media_id": media.get("id"),
            "caption": str(media.get("caption") or "")[:280],
            "published_at": media.get("timestamp"),
            "like_count": media.get("like_count", 0),
            "comments_count": media.get("comments_count", 0),
            "media_type": media.get("media_type"),
            "permalink": media.get("permalink"),
        }

    def capture_once(self, limit=10):
        try:
            overview = self.overview_reader()
            media = self.media_reader(limit=limit)
        except Exception as exc:
            return {"stage": "fetch-failed", "error": str(exc), "recorded": 0}

        previous = self._latest_snapshots()
        recorded = []

        account = self._account_snapshot(overview)
        if account != previous["account"]:
            recorded.append(self.memory.remember(
                category=self.CATEGORY,
                content=json.dumps(account, ensure_ascii=False, sort_keys=True),
                memory_type="observation",
                source=self.SOURCE,
                importance=3,
                tags=["instagram", "audience", "metrics"],
            ))

        for item in media:
            snapshot = self._media_snapshot(item)
            if snapshot == previous["media"].get(snapshot["media_id"]):
                continue
            recorded.append(self.memory.remember(
                category=self.CATEGORY,
                content=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                memory_type="observation",
                source=self.SOURCE,
                importance=2,
                tags=["instagram", "post", "metrics"],
            ))

        from brain.growth import GrowthEngine
        growth = GrowthEngine(self.memory).reflect_once()
        from brain.content_attribution import ContentAttributionEngine
        attribution = ContentAttributionEngine(self.memory).capture_instagram_once()

        return {
            "stage": "captured" if recorded else "no-changes",
            "recorded": len(recorded),
            "overview": account,
            "growth": growth,
            "attribution": attribution,
        }


class FacebookFeedbackCycle:
    """Records only changed Facebook Page counters, never repeated snapshots.

    Added 2026-10-04: AION recorded Instagram and YouTube audience numbers but
    nothing at all for its Facebook Page, so any decision about what Facebook
    should do (community questions, topic testing, Thai-first) would have been
    a guess. Read-only; no publishing side effect.

    Uses its own `kind` values ("facebook-page", "facebook-post") and source so
    the Instagram consumers (growth, attribution, dashboard), which key on
    kind == "account"/"media", never mistake these for Instagram snapshots.
    """

    CATEGORY = "social_feedback"
    SOURCE = "facebook-feedback"

    def __init__(self, memory, overview_reader, posts_reader):
        self.memory = memory
        self.overview_reader = overview_reader
        self.posts_reader = posts_reader

    def _latest_snapshots(self):
        snapshots = {"page": None, "posts": {}}
        try:
            entries = self.memory.all(self.CATEGORY)
        except Exception:
            entries = []
        for entry in entries:
            if entry.get("source") != self.SOURCE:
                continue
            try:
                data = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if data.get("kind") == "facebook-page":
                snapshots["page"] = data
            elif data.get("kind") == "facebook-post" and data.get("post_id"):
                snapshots["posts"][data["post_id"]] = data
        return snapshots

    @staticmethod
    def _page_snapshot(overview):
        return {
            "kind": "facebook-page",
            "name": overview.get("name"),
            "fan_count": overview.get("fan_count"),
            "followers_count": overview.get("followers_count"),
        }

    @staticmethod
    def _post_snapshot(post):
        return {
            "kind": "facebook-post",
            "post_id": post.get("id"),
            "message": str(post.get("message") or "")[:280],
            "published_at": post.get("created_time"),
            "reactions": post.get("reactions", 0),
            "comments": post.get("comments", 0),
            "shares": post.get("shares", 0),
            "permalink": post.get("permalink_url"),
        }

    def capture_once(self, limit=10):
        try:
            overview = self.overview_reader()
            posts = self.posts_reader(limit=limit)
        except Exception as exc:
            return {"stage": "fetch-failed", "error": str(exc), "recorded": 0}

        previous = self._latest_snapshots()
        recorded = []

        page = self._page_snapshot(overview)
        if page != previous["page"]:
            recorded.append(self.memory.remember(
                category=self.CATEGORY,
                content=json.dumps(page, ensure_ascii=False, sort_keys=True),
                memory_type="observation",
                source=self.SOURCE,
                importance=3,
                tags=["facebook", "audience", "metrics"],
            ))

        for item in posts:
            snapshot = self._post_snapshot(item)
            if snapshot == previous["posts"].get(snapshot["post_id"]):
                continue
            recorded.append(self.memory.remember(
                category=self.CATEGORY,
                content=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                memory_type="observation",
                source=self.SOURCE,
                importance=2,
                tags=["facebook", "post", "metrics"],
            ))

        return {
            "stage": "captured" if recorded else "no-changes",
            "recorded": len(recorded),
            "overview": page,
            "posts_seen": len(posts),
        }

