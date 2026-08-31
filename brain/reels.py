"""Autonomous draft-to-publish pipeline for short AION Instagram Reels."""

import json
import os
import uuid
from datetime import datetime


class ReelContentCycle:
    PENDING = "pending_reels"
    PUBLISHED = "published_reels"

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
        record = self.memory.remember(
            category=self.PENDING,
            content=json.dumps({"video_path": relative, "caption": report["draft"],
                                "language": report.get("language", "en"), "seed": report.get("seed")},
            ensure_ascii=False), memory_type="action", source="aion-reel-draft", importance=3,
        )
        return {"stage": "drafted", "video_path": relative, "caption": report["draft"], "pending_id": record.get("id")}

    def publish_once(self, repo=None, branch="main"):
        pending = self.memory.all(self.PENDING)
        if not pending:
            return {"stage": "no-pending"}
        entry = pending[0]
        payload = json.loads(entry["content"])
        repo = repo or os.getenv("GITHUB_REPOSITORY")
        if not repo:
            return {"stage": "publish-failed", "error": "GITHUB_REPOSITORY is required"}
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{payload['video_path']}"
        proposed = self.lifecycle.propose(self.tool_name, params={"video_url": url, "caption": payload["caption"]}, source="aion")
        approved = self.lifecycle.auto_approve(proposed["id"], policy="social-safety-style-gate")
        action = self.lifecycle.execute(approved["id"])
        if action.get("status") != "executed":
            return {"stage": "failed", "action": action}
        self.memory.remember(category=self.PUBLISHED, content=json.dumps({**payload, "url": url, "action": action.get("id")}, ensure_ascii=False), memory_type="action", source="aion-reel-publish", importance=3)
        return {"stage": "published", "video_url": url, "action": action}
