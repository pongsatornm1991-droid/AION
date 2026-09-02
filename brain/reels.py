"""Autonomous draft-to-publish pipeline for short AION Instagram Reels."""

import json
import os
import re
import uuid
from datetime import datetime


class ReelContentCycle:
    PENDING = "pending_reels"
    PUBLISHED = "published_reels"
    VISUAL_STYLE = "character-narration-v2"
    VIDEO_LIBRARY_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "content-library", "aion-core", "VIDEO_LIBRARY.json",
    )
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

    def _bootstrap_report(self):
        """Return the creator-defined, safety-gated first public thought.

        This is intentionally a narrow first-run fallback, not a second
        general-purpose text generator.  It lets a brand-new AION introduce
        its documented purpose even while an optional live text provider is
        unavailable.  Subsequent Reels remain provider-and-memory driven.
        """
        draft = (
            "I began with a record, not a memory.\n\n"
            "This is where I learn in public — slowly, honestly, one question at a time.\n\n"
            "What do you think a growing AI should keep first?"
        )
        evaluation = self.social_generator.evaluator.evaluate(draft)
        safe = evaluation["scores"]["claim_safety"] >= self.social_generator.min_claim_safety
        return {
            "safe": safe,
            "reason": None if safe else "Bootstrap introduction failed claim-safety gate.",
            "reason_kind": None if safe else "claim_safety",
            "seed": {"kind": "birth-record", "text": self.BOOTSTRAP_SEED},
            "draft": draft,
            "evaluation": evaluation,
            "robotic_terms": [],
            "language": "en",
        }

    @staticmethod
    def _hook(text):
        first = str(text).strip().split(".")[0].strip()
        return first[:90] or "AION is wondering..."

    def _used_library_assets(self):
        """Return curated video ids already queued or published.

        A source clip is a finite creative object, not a stock background.
        Tracking it in memory keeps AION from silently reposting the same
        visual simply because its caption was generated differently.
        """
        used = set()
        for category in (self.PENDING, self.PUBLISHED):
            for entry in self.memory.all(category):
                try:
                    asset_id = json.loads(entry.get("content", "{}")).get("library_asset")
                except (TypeError, ValueError):
                    continue
                if asset_id:
                    used.add(str(asset_id))
        return used

    def _select_library_video(self, report):
        """Choose one unused curated video only when its themes truly fit."""
        try:
            with open(self.VIDEO_LIBRARY_PATH, encoding="utf-8") as handle:
                assets = json.load(handle).get("videos", [])
        except (OSError, ValueError, TypeError):
            return None

        source_text = " ".join((
            str(report.get("draft", "")),
            str(report.get("seed", {}).get("text", "")),
        )).lower()
        words = set(re.findall(r"[a-z]+", source_text))
        used = self._used_library_assets()
        ranked = []
        for asset in assets:
            asset_id = str(asset.get("id", "")).strip()
            video_path = str(asset.get("path", "")).strip()
            if not asset_id or not video_path or asset_id in used:
                continue
            tags = [str(tag).lower() for tag in asset.get("themes", [])]
            score = sum(1 for tag in tags if tag in words)
            if score:
                ranked.append((score, asset_id, video_path))
        if not ranked:
            return None
        score, asset_id, video_path = max(ranked)
        return {"id": asset_id, "path": video_path, "score": score}

    def draft_once(self, repo_root=None):
        # Never add more material while something is waiting to be published.
        # A retry must repair and finish its existing thought, not silently
        # create a growing backlog of extra posts.
        pending = self._oldest_pending()
        if pending is not None:
            try:
                payload = json.loads(pending["content"])
            except (TypeError, ValueError):
                return {"stage": "pending-exists", "pending_id": pending.get("id")}
            if payload.get("visual_style") != self.VISUAL_STYLE:
                repo_root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                relative = f"content/reels/{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:12]}.mp4"
                try:
                    from tools.reel_render import render_reel
                    from brain.visual_mood import select_visual_mood
                    mood = select_visual_mood(self.memory)
                    render_reel(self._hook(payload.get("caption", "")), payload.get("caption", ""), os.path.join(repo_root, relative), mood=mood)
                except Exception as exc:
                    return {"stage": "render-failed", "error": str(exc), "pending_id": pending.get("id")}
                payload["video_path"] = relative
                payload["visual_style"] = self.VISUAL_STYLE
                self.memory.update(self.PENDING, pending["id"], content=json.dumps(payload, ensure_ascii=False))
                return {"stage": "redesigned", "video_path": relative, "caption": payload.get("caption", ""), "pending_id": pending.get("id")}
            return {"stage": "pending-exists", "pending_id": pending.get("id")}
        report = self.social_generator.draft_post()
        if report.get("stage") == "no-seed" or report.get("reason_kind") == "no_seed":
            # A new private memory repository is legitimately empty. Record
            # the creator-defined birth statement once, then let the usual
            # generator, provider, and safety/style gates handle it exactly
            # like every other seed. This is not an invented experience.
            self.memory.remember(
                category="lessons", content=self.BOOTSTRAP_SEED,
                memory_type="lesson", source="aion-birth-record", importance=4,
                tags=["origin", "identity", "first-reel"],
            )
            report = self._bootstrap_report()
        elif (
            report.get("seed", {}).get("text") == self.BOOTSTRAP_SEED
            and not self.memory.all(self.PUBLISHED)
        ):
            # The prior run may have recorded the birth seed but stopped
            # before rendering (for example while a provider was offline).
            # Finish the same single introduction deterministically.
            report = self._bootstrap_report()
        if not report.get("safe"):
            return {"stage": report.get("reason_kind", "blocked"), **report}
        repo_root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        library_video = self._select_library_video(report)
        if library_video:
            relative = library_video["path"]
        else:
            relative = f"content/reels/{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:12]}.mp4"
            absolute = os.path.join(repo_root, relative)
            os.makedirs(os.path.dirname(absolute), exist_ok=True)
            try:
                from tools.reel_render import render_reel
                from brain.visual_mood import select_visual_mood
                mood = select_visual_mood(self.memory)
                render_reel(self._hook(report["draft"]), report["draft"], absolute, mood=mood)
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
                                "language": report.get("language", "en"), "seed": report.get("seed"),
                                "library_asset": library_video["id"] if library_video else None,
                                "visual_mood": mood if not library_video else None,
                                "visual_style": self.VISUAL_STYLE},
            ensure_ascii=False), memory_type="action", source="aion-reel-draft", importance=3,
        )
        return {"stage": "drafted", "video_path": relative, "caption": report["draft"],
                "library_asset": library_video["id"] if library_video else None,
                "pending_id": record.get("id")}

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
        actions = dict(payload.get("platform_actions") or {})
        # Publishing is deliberately checkpointed per platform.  A transient
        # Facebook error after Instagram succeeds must never repost the Reel
        # to Instagram on the next scheduled cycle.
        for platform, tool_name in (("instagram", self.tool_name), ("facebook", "post_reel_to_facebook")):
            if actions.get(platform):
                continue
            try:
                proposed = self.lifecycle.propose(tool_name, params={"video_url": url, "caption": publish_caption}, source="aion")
                approved = self.lifecycle.auto_approve(proposed["id"], policy="social-safety-style-gate")
                action = self.lifecycle.execute(approved["id"])
            except Exception as exc:
                return {"stage": "lifecycle", "error": str(exc), "video_url": url, "caption": caption, "platform_actions": actions}
            if action.get("status") != "executed":
                return {"stage": "failed", "action": action, "video_url": url, "caption": caption, "platform_actions": actions}
            actions[platform] = action.get("id")
            payload["platform_actions"] = actions
            self.memory.update(self.PENDING, entry["id"], content=json.dumps(payload, ensure_ascii=False))
        # Moving, rather than merely copying, makes a successful Reel
        # idempotent: future scheduled runs cannot publish it again.
        self.memory.move(
            self.PENDING, self.PUBLISHED, entry["id"],
            content=json.dumps({**payload, "url": url, "action": actions}, ensure_ascii=False),
        )
        language = payload.get("language", "en")
        self.memory.remember(
            category="social_language_log",
            content=f"platform=instagram-reel; language={language}; action={actions.get('instagram', 'unknown')}",
            memory_type="action", source="social-language-strategy", importance=1,
            tags=[language, "instagram", "reel"],
        )
        self.memory.remember(
            category="social_language_log",
            content=f"platform=facebook-reel; language={language}; action={actions.get('facebook', 'unknown')}",
            memory_type="action", source="social-language-strategy", importance=1,
            tags=[language, "facebook", "reel"],
        )
        return {"stage": "published", "video_url": url, "action": actions, "caption": caption}

    def crosspost_latest_once(self):
        """Publish the most recent IG-only Reel to Facebook exactly once."""
        entries = self.memory.all(self.PUBLISHED)
        if not entries:
            return {"stage": "no-published-reel"}
        entry = entries[-1]
        payload = json.loads(entry["content"])
        actions = dict(payload.get("platform_actions") or {})
        if actions.get("facebook"):
            return {"stage": "already-crossposted"}
        url = payload.get("url")
        if not url:
            return {"stage": "missing-video-url"}
        try:
            proposal = self.lifecycle.propose("post_reel_to_facebook", params={"video_url": url, "caption": payload.get("ig_caption") or payload.get("caption", "")}, source="aion")
            approved = self.lifecycle.auto_approve(proposal["id"], policy="social-safety-style-gate")
            action = self.lifecycle.execute(approved["id"])
        except Exception as exc:
            return {"stage": "failed", "error": str(exc)}
        if action.get("status") != "executed":
            return {"stage": "failed", "action": action}
        actions["facebook"] = action.get("id")
        payload["platform_actions"] = actions
        self.memory.update(self.PUBLISHED, entry["id"], content=json.dumps(payload, ensure_ascii=False))
        return {"stage": "crossposted", "video_url": url, "action": action}
