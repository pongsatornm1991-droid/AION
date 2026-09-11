"""Link observed platform response to the AION story that produced it."""

import json
import re


class ContentAttributionEngine:
    CATEGORY = "content_attribution"
    SOURCE = "aion-content-attribution"

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _normalise(text):
        text = re.sub(r"https?://\S+", "", str(text or "").lower())
        text = re.sub(r"#[\w]+", "", text)
        return " ".join(re.sub(r"[^\w\s\u0e00-\u0e7f]", " ", text).split())

    def _stories(self):
        stories = []
        for entry in self.memory.all("published_reels"):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            routes = payload.get("platform_captions") or {}
            content_id = routes.get("content_id")
            if not content_id:
                continue  # Legacy posts stay visible but are not guessed at.
            stories.append({
                "content_id": content_id,
                "captions": [payload.get("caption", ""), payload.get("ig_caption", ""), *routes.values()],
                "reel_memory_id": entry.get("id"),
            })
        return stories

    def _match(self, caption):
        observed = self._normalise(caption)
        if not observed:
            return None
        for story in self._stories():
            for candidate in story["captions"]:
                expected = self._normalise(candidate)
                if len(expected) >= 20 and (expected in observed or observed in expected):
                    return story
        return None

    def capture_instagram_once(self):
        captured = []
        for entry in self.memory.all("social_feedback"):
            try:
                metric = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if metric.get("kind") != "media" or not metric.get("media_id"):
                continue
            story = self._match(metric.get("caption"))
            if not story:
                continue
            payload = {
                "content_id": story["content_id"], "platform": "instagram",
                "media_id": metric["media_id"], "like_count": metric.get("like_count", 0),
                "comments_count": metric.get("comments_count", 0),
                "observed_at": entry.get("timestamp"), "reel_memory_id": story["reel_memory_id"],
            }
            source = f"{self.SOURCE}:instagram:{metric['media_id']}:{payload['like_count']}:{payload['comments_count']}"
            saved = self.memory.remember(
                self.CATEGORY, json.dumps(payload, ensure_ascii=False, sort_keys=True),
                memory_type="observation", source=source, importance=3,
                tags=["content-attribution", "instagram", story["content_id"]], related=[story["reel_memory_id"]],
            )
            if saved.get("saved"):
                captured.append(payload)
        return {"stage": "captured" if captured else "unchanged", "recorded": len(captured), "items": captured}
