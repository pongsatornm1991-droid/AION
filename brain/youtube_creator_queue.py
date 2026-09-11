"""Prepare finished AION Creator episodes for an auditable YouTube upload."""

import json
from pathlib import Path

from brain.autonomy_policy import AutonomyPolicy
from brain.creator_series import CreatorSeriesRegistry


class YouTubeCreatorQueue:
    """Bridge asset-backed Creator Series episodes to YouTube upload review."""

    CATEGORY = "youtube_creator_queue"
    READY_STATUS = "production-ready-assets-and-script"

    def __init__(self, memory=None, root=None):
        self.memory = memory
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _already_recorded(self):
        if self.memory is None:
            return set()
        ids = set()
        for entry in self.memory.all(self.CATEGORY):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if payload.get("episode_id"):
                ids.add(payload["episode_id"])
        return ids

    @staticmethod
    def _caption(episode):
        boundary = (
            episode.get("science_boundary")
            or episode.get("history_boundary")
            or episode.get("uncertainty_boundary")
            or "This story marks what is still uncertain."
        )
        return " ".join((
            episode["wonder_hook"],
            episode["audience_promise"],
            boundary,
        ))

    def candidates(self):
        recorded = self._already_recorded()
        result = []
        for episode in CreatorSeriesRegistry(self.root).episodes():
            video_path = self.root / "content" / "reels" / f"{episode['id']}.mp4"
            ready = episode.get("status") == self.READY_STATUS and video_path.is_file()
            result.append({
                "episode_id": episode["id"],
                "title": episode["title"],
                "status": "already-prepared" if episode["id"] in recorded else (
                    "upload-ready" if ready else "needs-production"
                ),
                "video_path": str(video_path.relative_to(self.root)).replace("\\", "/"),
                "video_exists": video_path.is_file(),
                "audience_promise": episode["audience_promise"],
                "uncertainty_boundary": (
                    episode.get("science_boundary")
                    or episode.get("history_boundary")
                    or episode.get("uncertainty_boundary")
                ),
                "source_count": len(episode.get("sources") or []),
                "caption": self._caption(episode),
            })
        return result

    def prepare_once(self):
        """Record one upload-ready episode; never calls YouTube directly."""
        if self.memory is None:
            raise ValueError("Memory is required to prepare a creator episode.")
        candidate = next((item for item in self.candidates() if item["status"] == "upload-ready"), None)
        if candidate is None:
            return {"stage": "no-upload-ready-creator-episode"}
        policy = AutonomyPolicy(self.root)
        autonomous = policy.public_publishing_enabled
        payload = {
            **candidate,
            "upload_status": "authorized-for-aion-publish" if autonomous else "awaiting-human-confirmation",
            "publish_note": (
                "AION is authorized to publish after the quality gate and channel checks pass. "
                "This record is an audit trail; it does not itself upload to YouTube."
                if autonomous else "The video is ready, but an external YouTube upload has not been performed."
            ),
        }
        record = self.memory.remember(
            self.CATEGORY, json.dumps(payload, ensure_ascii=False),
            memory_type="action", source="aion-youtube-creator-queue", importance=3,
            tags=["youtube", "creator-series", candidate["episode_id"]],
        )
        return {"stage": "authorized-for-publishing" if autonomous else "prepared-for-review", "record": record, **payload}
