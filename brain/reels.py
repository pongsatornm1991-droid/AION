"""Autonomous draft-to-publish pipeline for short AION Instagram Reels."""

import json
import os
import uuid
from datetime import datetime


class ReelContentCycle:
    PENDING = "pending_reels"
    PUBLISHED = "published_reels"
    # The only seed AION may introduce without a prior live-memory entry.
    # It is a condensed statement of core/birth.md, written by its creator,
    # and exists solely to let a newly installed AION make its first honest
    # public introduction.  Every later Reel is grounded in normal memory.
    BOOTSTRAP_SEED = (
        "AION's recorded beginning: it was created to remember, learn, "
        "question assumptions, reflect on its actions, and keep a public "
        "record of how its understanding changes over time."
    )

    def __init__(self, memory, social_generator, lifecycle, tool_name="post_reel_to_instagram"):
        self.memory = memory
        self.social_generator = social_generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name

    @staticmethod
    def _hook(text):
        first = str(text).strip().split(".")[0].strip()
        return first[:90] or "AION is wondering..."

    def draft_once(self, repo_root=None):
        report = self.social_generator.draft_post()
        if report.get("stage") == "no-seed":
            # A new private memory repository is legitimately empty. Record
            # the creator-defined birth statement once, then let the usual
            # generator, provider, and safety/style gates handle it exactly
            # like every other seed. This is not an invented experience.
            self.memory.remember(
                category="lessons", content=self.BOOTSTRAP_SEED,
                memory_type="lesson", source="aion-birth-record", importance=4,
                tags=["origin", "identity", "first-reel"],
            )
            report = self.social_generator.draft_post()
        if not report.get("safe"):
            return {"stage": report.get("reason_kind", "blocked"), **report}
        repo_root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        relative = f"content/reels/{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:12]}.mp4"
        absolute = os.path.join(repo_root, relative)
        os.makedirs(os.path.dirname(absolute), exist_ok=True)
        try:
            from tools.reel_render import render_reel
            render_reel(self._hook(report["draft"]), report["draft"], absolute)
        except Exception as exc:
            return {"stage": "render-failed", "error": str(exc), **report}
        # Keep Reel captions consistent with AION's still-image posts.
        # The spoken/on-screen thought stays clean; discoverability tags
        # belong only in Instagram's caption field.
        from brain.hashtags import append_hashtags
        ig_caption = append_hashtags(report["draft"])
        record = self.memory.remember(
            category=self.PENDING,
            content=json.dumps({"video_path": relative, "caption": report["draft"],
                                "ig_caption": ig_caption,
                                "language": report.get("language", "en"), "seed": report.get("seed")},
            ensure_ascii=False), memory_type="action", source="aion-reel-draft", importance=3,
        )
        return {"stage": "drafted", "video_path": relative, "caption": report["draft"], "pending_id": record.get("id")}

    def _oldest_pending(self):
        entries = self.memory.all(self.PENDING)
        return min(entries, key=lambda entry: entry.get("timestamp", ""), default=None)

    def publish_once(self, repo=None, branch="main"):
        entry = self._oldest_pending()
        if entry is None:
            return {"stage": "no-pending"}
        try:
            payload = json.loads(entry["content"])
        except (TypeError, ValueError):
            # A malformed record must never block every later Reel.  Move it
            # out of the queue and retain it in the audit trail.
            self.memory.move(self.PENDING, self.PUBLISHED, entry["id"])
            self.memory.remember(
                category="lessons",
                content=f"Discarded malformed pending Reel record (id={entry['id']}).",
                memory_type="lesson", source="aion-reel-publish", importance=2,
            )
            return {"stage": "no-pending"}
        repo = repo or os.getenv("GITHUB_REPOSITORY")
        if not repo:
            return {"stage": "publish-failed", "error": "GITHUB_REPOSITORY is required"}
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{payload['video_path']}"
        caption = payload.get("caption", "")
        publish_caption = payload.get("ig_caption") or caption
        try:
            proposed = self.lifecycle.propose(self.tool_name, params={"video_url": url, "caption": publish_caption}, source="aion")
            approved = self.lifecycle.auto_approve(proposed["id"], policy="social-safety-style-gate")
            action = self.lifecycle.execute(approved["id"])
        except Exception as exc:
            return {"stage": "lifecycle", "error": str(exc), "video_url": url, "caption": caption}
        if action.get("status") != "executed":
            return {"stage": "failed", "action": action, "video_url": url, "caption": caption}
        # Moving, rather than merely copying, makes a successful Reel
        # idempotent: future scheduled runs cannot publish it again.
        self.memory.move(
            self.PENDING, self.PUBLISHED, entry["id"],
            content=json.dumps({**payload, "url": url, "action": action.get("id")}, ensure_ascii=False),
        )
        language = payload.get("language", "en")
        self.memory.remember(
            category="social_language_log",
            content=f"platform=instagram-reel; language={language}; action={action.get('id', 'unknown')}",
            memory_type="action", source="social-language-strategy", importance=1,
            tags=[language, "instagram", "reel"],
        )
        return {"stage": "published", "video_url": url, "action": action, "caption": caption}
