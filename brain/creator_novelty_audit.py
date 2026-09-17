"""Retire unfinished Studio episodes that duplicate a published subject.

Research already checks novelty before it creates a brief.  This second gate
protects the production queue when an older storyboard predates that check or
when publishing evidence arrives after the storyboard was saved.
"""

import json
from pathlib import Path

from brain.content_novelty import ContentNoveltyLedger


class CreatorNoveltyAudit:
    """Keep public-topic duplicates out of the image and audio production queue."""

    RETIRABLE_STATES = {"storyboard-ready-needs-assets", "assets-ready-for-assembly"}

    def __init__(self, memory, root):
        self.memory = memory
        self.root = Path(root)
        self.directory = self.root / "content" / "creator_series"

    @staticmethod
    def _candidate(episode):
        return {
            "topic_key": episode.get("topic_key") or episode.get("wonder_hook") or episode.get("title"),
            "title": episode.get("title"),
            "story_package_id": episode.get("story_package_id"),
            "content_angle_key": episode.get("content_angle_key"),
            "source_urls": [
                source.get("url") for source in (episode.get("sources") or [])
                if source.get("url")
            ],
        }

    def audit(self):
        ledger = ContentNoveltyLedger(self.memory)
        retired, retained = [], []
        for path in sorted(self.directory.glob("*.json")):
            try:
                episode = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            if episode.get("status") not in self.RETIRABLE_STATES:
                continue
            decision = ledger.assess(self._candidate(episode))
            if decision.get("eligible"):
                retained.append(episode.get("id"))
                continue
            episode["status"] = "retired-do-not-publish"
            episode["retirement_reason"] = "duplicate-topic-company-wide"
            episode["novelty_audit"] = {
                "state": "blocked",
                "reason": decision.get("reason"),
                "matches": decision.get("matches") or [],
            }
            path.write_text(json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            retired.append({"episode_id": episode.get("id"), "matches": decision.get("matches") or []})
        return {
            "stage": "duplicate-storyboards-retired" if retired else "no-duplicate-storyboards",
            "retired": retired,
            "retained": retained,
        }
