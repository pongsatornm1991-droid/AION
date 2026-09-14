"""Capture public YouTube outcome signals for AION's own published work."""

import json


class YouTubeAudienceCycle:
    """Persist only changed public statistics; never invent retention data."""

    CATEGORY = "social_feedback"
    SOURCE = "youtube-public-analytics"

    def __init__(self, memory, statistics_reader=None):
        self.memory = memory
        if statistics_reader is None:
            from tools.youtube_discovery import get_youtube_video_statistics
            statistics_reader = get_youtube_video_statistics
        self.statistics_reader = statistics_reader

    def _published_ids(self):
        ids = []
        for entry in self.memory.all("youtube_creator_queue"):
            try:
                payload = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            video_id = str(((payload.get("youtube") or {}).get("video_id") or "")).strip()
            if video_id and video_id not in ids:
                ids.append(video_id)
        return ids

    def _latest(self):
        latest = {}
        for entry in self.memory.all(self.CATEGORY):
            if entry.get("source") != self.SOURCE:
                continue
            try:
                payload = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if isinstance(payload, dict) and payload.get("video_id"):
                latest[payload["video_id"]] = payload
        return latest

    def capture_once(self):
        video_ids = self._published_ids()
        if not video_ids:
            return {"stage": "no-published-aion-youtube-video", "recorded": 0}
        try:
            rows = self.statistics_reader(video_ids)
        except RuntimeError as exc:
            return {"stage": "configuration-needed" if "YOUTUBE_DATA_API_KEY" in str(exc) else "fetch-failed", "recorded": 0, "error": str(exc)}
        except Exception as exc:
            return {"stage": "fetch-failed", "recorded": 0, "error": str(exc)}

        prior, saved = self._latest(), []
        for row in rows:
            snapshot = {
                "kind": "youtube-public-video", "video_id": row.get("video_id"),
                "title": str(row.get("title") or "")[:240],
                "published_at": row.get("published_at"),
                "view_count": int(row.get("view_count") or 0),
                "like_count": int(row.get("like_count") or 0),
                "comment_count": int(row.get("comment_count") or 0),
                "epistemic_boundary": "Public statistics only. Retention and audience demographics require YouTube Analytics authorization and are never inferred from views.",
            }
            if snapshot == prior.get(snapshot["video_id"]):
                continue
            saved.append(self.memory.remember(
                self.CATEGORY, json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                memory_type="observation", source=self.SOURCE, importance=2,
                tags=["youtube", "audience", "public-metrics", snapshot["video_id"]],
            ))
        return {"stage": "captured" if saved else "no-changes", "recorded": len(saved), "videos": len(rows)}
