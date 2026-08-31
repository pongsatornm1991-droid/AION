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

        return {
            "stage": "captured" if recorded else "no-changes",
            "recorded": len(recorded),
            "overview": account,
            "growth": growth,
        }
