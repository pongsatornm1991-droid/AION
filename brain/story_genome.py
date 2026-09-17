"""Read-only map of AION's subjects, angles and reusable story evidence."""

from brain.content_novelty import ContentNoveltyLedger
from brain.creator_series import CreatorSeriesRegistry


class StoryGenome:
    """Expose company-wide content memory without creating a second queue."""

    def __init__(self, memory, root):
        self.memory = memory
        self.root = root

    def snapshot(self):
        episodes = CreatorSeriesRegistry(self.root).episodes()
        records = ContentNoveltyLedger(self.memory).records()
        topics = []
        for episode in episodes:
            topics.append({
                "episode_id": episode.get("id"),
                "topic": episode.get("topic_key") or episode.get("wonder_hook") or episode.get("title"),
                "angle": episode.get("content_angle_key") or "unspecified",
                "state": episode.get("status"),
            })
        return {
            "version": "story-genome-v1",
            "topics": topics,
            "tracked_public_or_queued_records": len(records),
            "rule": "หัวข้อซ้ำถูกตรวจจากผลงานเผยแพร่ คิวเผยแพร่ และ storyboard ก่อนเริ่มผลิตภาพ",
        }
