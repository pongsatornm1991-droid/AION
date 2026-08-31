"""Turn audience observations into modest, evidence-bound posting guidance."""

import json


class GrowthEngine:
    """Derive one cautious insight from real Instagram observations."""

    FEEDBACK_CATEGORY = "social_feedback"
    CATEGORY = "growth_insights"
    SOURCE = "aion-growth-engine"
    MIN_MEDIA = 3

    def __init__(self, memory):
        self.memory = memory

    def _media(self):
        items = []
        for entry in self.memory.all(self.FEEDBACK_CATEGORY):
            try:
                data = json.loads(entry.get("content") or "")
            except (TypeError, ValueError):
                continue
            if data.get("kind") == "media" and data.get("media_id"):
                items.append(data)
        return list({item["media_id"]: item for item in items}.values())

    @staticmethod
    def _score(item):
        return int(item.get("like_count") or 0) + 3 * int(item.get("comments_count") or 0)

    def reflect_once(self):
        media = self._media()
        if len(media) < self.MIN_MEDIA:
            return {"stage": "insufficient-data", "media_count": len(media)}

        best = max(media, key=self._score)
        guidance = (
            "Audience evidence: the strongest observed Instagram response so far was "
            f"to this theme/caption: {best.get('caption', '')[:180]}. Use it only as "
            "gentle inspiration; preserve AION's manifesto, evidence, and variety."
        )
        signature = json.dumps(
            {"best": best.get("media_id"), "score": self._score(best), "guidance": guidance},
            ensure_ascii=False, sort_keys=True,
        )
        if signature in [entry.get("content") for entry in self.memory.all(self.CATEGORY)]:
            return {"stage": "unchanged", "media_count": len(media), "guidance": guidance}

        record = self.memory.remember(
            category=self.CATEGORY, content=signature, memory_type="lesson",
            source=self.SOURCE, importance=3, tags=["growth", "instagram", "evidence"],
        )
        return {"stage": "learned", "media_count": len(media), "guidance": guidance, "id": record.get("id")}
