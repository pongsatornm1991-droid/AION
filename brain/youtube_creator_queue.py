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

    def _records_by_episode(self):
        """Return the latest durable queue record for each Creator episode."""
        records = {}
        if self.memory is None:
            return records
        for entry in self.memory.all(self.CATEGORY):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            episode_id = payload.get("episode_id")
            if episode_id:
                records[episode_id] = (entry, payload)
        return records

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
        recorded = self._records_by_episode()
        result = []
        for episode in CreatorSeriesRegistry(self.root).episodes():
            video_path = self.root / "content" / "reels" / f"{episode['id']}.mp4"
            ready = episode.get("status") == self.READY_STATUS and video_path.is_file()
            previous = recorded.get(episode["id"])
            result.append({
                "episode_id": episode["id"],
                "title": episode["title"],
                "status": "published" if previous and (previous[1].get("youtube") or {}).get("video_id") else "already-prepared" if previous else (
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
                "viewer_value": episode["audience_promise"],
                "visual_style": "illustrated-aion-storyboard-v4",
                # Queue state is durable and is the source of truth for the
                # UI.  Keep the friendly display status above for legacy
                # screens, but never discard the authorization state.
                "publication_status": previous[1].get("upload_status") if previous else None,
            })
        return result

    def prepare_once(self):
        """Record one upload-ready episode; never calls YouTube directly."""
        if self.memory is None:
            raise ValueError("Memory is required to prepare a creator episode.")
        policy = AutonomyPolicy(self.root)
        # Records created before public publishing was delegated must not be
        # stranded behind the former per-item confirmation rule.  Promote the
        # durable record in place; this changes no credentials and performs no
        # upload, but leaves a clear audit trail for the later publish step.
        if policy.public_publishing_enabled:
            legacy = next((item for item in self._records_by_episode().values()
                           if item[1].get("upload_status") == "awaiting-human-confirmation"), None)
            if legacy is not None:
                entry, payload = legacy
                updated = {
                    **payload,
                    "upload_status": "authorized-for-aion-publish",
                    "publish_note": "Authorization migrated from the former owner-confirmation policy; quality and channel checks still apply.",
                }
                self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
                return {"stage": "authorized-for-publishing", "migrated": True, **updated}
        candidate = next((item for item in self.candidates() if item["status"] == "upload-ready"), None)
        if candidate is None:
            return {"stage": "no-upload-ready-creator-episode"}
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

    def publish_once(self, uploader=None):
        """Upload one authorized Creator episode exactly once."""
        if self.memory is None:
            raise ValueError("Memory is required to publish a creator episode.")
        if not AutonomyPolicy(self.root).public_publishing_enabled:
            return {"stage": "owner-policy-required"}
        target = next((item for item in self._records_by_episode().values()
                       if item[1].get("upload_status") == "authorized-for-aion-publish"
                       and not (item[1].get("youtube") or {}).get("video_id")), None)
        if target is None:
            return {"stage": "no-authorized-creator-episode"}
        entry, payload = target
        path = self.root / str(payload.get("video_path") or "")
        if not path.is_file():
            return {"stage": "missing-video", "episode_id": payload.get("episode_id")}
        from brain.youtube_quality import YouTubeQualityGate
        prior = [record for _, record in self._records_by_episode().values()
                 if (record.get("youtube") or {}).get("video_id")]
        quality = YouTubeQualityGate().assess(payload, prior)
        if not quality["eligible"]:
            return {"stage": "quality-review-required", "episode_id": payload.get("episode_id"), **quality}
        description = "\n\n".join(part for part in (
            payload.get("caption"),
            "Original illustrated AION story. AI disclosure reviewed before publication.",
            "#Shorts #AION #AI",
        ) if part)
        try:
            if uploader is None:
                from tools.youtube import upload_short
                uploader = upload_short
            result = uploader(str(path), str(payload.get("title") or "AION Wonders"), description)
        except Exception as exc:
            return {"stage": "upload-failed", "episode_id": payload.get("episode_id"), "error": str(exc)}
        updated = {**payload, "youtube": {**result, "quality": quality}, "upload_status": "published"}
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
        self.memory.remember(
            "social_language_log",
            f"platform=youtube-creator; episode={updated.get('episode_id')}; video={result.get('video_id', 'unknown')}",
            memory_type="action", source="aion-youtube-creator-publish", importance=1,
            tags=["youtube", "creator-series", updated.get("episode_id", "unknown")],
        )
        return {"stage": "published", "episode_id": updated.get("episode_id"), **result}
