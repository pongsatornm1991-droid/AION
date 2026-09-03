"""Visual content pipeline -- the missing piece Instagram publishing
(tools/instagram.py, built 2026-08-30) has needed since it landed: a
way for AION to actually produce a real, publicly reachable image to
post, instead of only having the Graph API wrapper sitting unused.

Deliberately split into two independently-runnable stages, mirroring
Phase 12's propose/draft-then-approve/publish split:

1. VisualContentCycle.draft_once() -- decide what to say (reusing
   SocialContentGenerator's existing seed-pick + claim-safety +
   robotic-style gates verbatim, so a caption goes through exactly
   the same scrutiny as a Facebook post; no new drafting logic to
   duplicate or accidentally under-gate), then render it as a PNG
   card via tools/image_render.py, save it under content/images/ in
   THIS repo (the public code repo, not the private memory_data
   repo), and record a "pending_visual_content" memory entry
   describing what was drawn and where. No Instagram API call
   happens here.

2. VisualContentCycle.publish_once() -- find that pending record,
   build the image's public raw.githubusercontent.com URL, and only
   THEN call tools.instagram.publish_photo() through the same
   propose -> approve("auto-safety-gate") -> execute ToolLifecycle
   discipline every other posting action in this codebase uses.

The two stages exist separately because the image file has to
actually be committed and pushed to origin/main -- and Instagram's
CDN-fetch of that raw URL needs a moment to see the new commit --
between drafting and publishing; main.py's two CLI commands
(run-instagram-draft / run-instagram-publish) are meant to be run by
a GitHub Actions workflow with a `git push` and a short sleep in
between, not back-to-back in one process. See
.github/workflows/instagram-cycle.yml.

Deliberately does NOT decide hosting via Imgur or any other third
service: raw.githubusercontent.com serves any file already in this
public repo for free, with no new credential for the user to create,
consistent with this project's free-tier-first, don't-add-unused-
credentials discipline (see tools/instagram.py's own docstring for
the same reasoning).
"""

import json
import os
import uuid
from datetime import datetime


PENDING_CATEGORY = "pending_visual_content"
PUBLISHED_CATEGORY = "published_visual_content"
PENDING_SOURCE = "aion-visual-draft"

IMAGES_DIR = "content/images"


class VisualContentCycle:
    """Orchestrates the draft -> render -> (git push happens outside
    this class, in the workflow) -> publish flow for one Instagram
    image post."""

    def __init__(self, memory, social_generator, lifecycle, tool_name="post_to_instagram"):
        self.memory = memory
        self.social_generator = social_generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name

    # ---------------------------------------------------------
    # STAGE 1: draft caption + render image, no network call
    # ---------------------------------------------------------

    def draft_once(self, seed=None, rng=None, repo_root=None):
        """Draft a caption (via the same gates SocialContentGenerator
        uses for Facebook posts) and, if it passes, render it into a
        PNG card under content/images/ in this repo. Returns a report
        dict with a "stage" key, matching every other cycle's
        run_once() convention in this codebase:

        - "no-seed" / "safety-gate" / "style-gate" / "draft-failed":
          no image was produced, same meaning as SocialAutoCycle's
          identically-named stages.
        - "drafted": an image was produced and a pending record was
          saved; report["image_path"] is repo-relative (safe to git
          add), report["caption"] is the text drawn on it.
        """

        try:
            draft_report = self.social_generator.draft_post(seed=seed, rng=rng)
        except Exception as exc:
            return {
                "stage": "draft-failed",
                "seed": None,
                "caption": None,
                "image_path": None,
                "error": str(exc),
            }

        if not draft_report["safe"]:
            reason_kind = draft_report.get("reason_kind")

            if reason_kind == "robotic_style":
                stage, source = "style-gate", "social-style-review"
            elif reason_kind == "no_seed":
                stage, source = "no-seed", None
            else:
                stage, source = "safety-gate", "social-safety-gate"

            if source is not None:
                self.memory.remember(
                    category="lessons",
                    content=(
                        f"Blocked a visual-content draft ({reason_kind}): "
                        f"{draft_report['reason']}"
                    ),
                    memory_type="lesson",
                    source=source,
                    importance=3,
                )

            return {
                "stage": stage,
                "seed": draft_report.get("seed"),
                "caption": None,
                "image_path": None,
                **{k: v for k, v in draft_report.items() if k not in ("seed",)},
            }

        caption = draft_report["draft"]

        image_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{timestamp}-{image_id}.png"
        relative_path = f"{IMAGES_DIR}/{filename}"

        if repo_root is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        absolute_path = os.path.join(repo_root, relative_path)

        # OpenAI image generation is opt-in and may fail transiently.  The
        # deterministic branded card keeps every scheduled run publishable
        # without spending a retry or losing AION's visual identity.
        from tools.openai_image import generate_social_image
        generated_by = "openai" if generate_social_image(caption, absolute_path) else "branded-card"
        if generated_by == "branded-card":
            from tools.image_render import render_content_card
            render_content_card(caption, absolute_path)

        from brain.hashtags import append_hashtags

        # "caption" (rendered onto the image card, and shown in
        # reports/Telegram notifications) is kept hashtag-free on
        # purpose -- a hashtag block drawn onto the card itself would
        # clutter the visual design. "ig_caption" is the separate,
        # hashtag-appended text actually sent to the Instagram Graph
        # API as the post's real caption (see publish_once() below).
        from brain.cross_platform import append_invitation
        ig_caption = append_hashtags(append_invitation(caption, "instagram", self.memory))

        record = self.memory.remember(
            category=PENDING_CATEGORY,
            content=json.dumps(
                {
                    "image_path": relative_path,
                    "caption": caption,
                    "ig_caption": ig_caption,
                    "seed": draft_report.get("seed"),
                    "language": draft_report.get("language", "th"),
                    "image_provider": generated_by,
                },
                ensure_ascii=False,
            ),
            memory_type="action",
            source=PENDING_SOURCE,
            importance=3,
        )

        return {
            "stage": "drafted",
            "seed": draft_report.get("seed"),
            "caption": caption,
            "image_provider": generated_by,
            "image_path": relative_path,
            "pending_id": record.get("id"),
        }

    # ---------------------------------------------------------
    # STAGE 2: publish the already-committed image to Instagram
    # ---------------------------------------------------------

    def _oldest_pending(self):
        entries = self.memory.all(PENDING_CATEGORY)
        if not entries:
            return None
        entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
        return entries[0]

    @staticmethod
    def _build_image_url(image_path, repo=None, branch="main"):
        repo = repo or os.getenv("GITHUB_REPOSITORY")
        if not repo:
            raise RuntimeError(
                "GITHUB_REPOSITORY is not set and no repo was given -- "
                "cannot build a public raw.githubusercontent.com URL "
                "for the pending image."
            )
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{image_path}"

    # Platforms published in this order, each checkpointed
    # independently in the pending record's own "platform_actions"
    # dict before moving on to the next -- mirrors
    # ReelContentCycle.publish_once()'s identical per-platform
    # checkpoint loop in brain/reels.py. A transient failure on one
    # platform after the other already succeeded must never repost to
    # the platform that already worked on a later retry.
    _PLATFORM_TOOLS = (("instagram", None), ("facebook", "post_photo_to_facebook"))

    def publish_once(self, repo=None, branch="main"):
        """Publish the oldest pending drafted image to Instagram AND
        Facebook (added 2026-09-03, at the user's request -- the two
        platforms had been fully separate pipelines since this cycle
        was first built; Instagram's own posts were never mirrored to
        the Facebook Page, unlike ReelContentCycle's video pipeline,
        which already cross-posts both platforms in one run).

        Returns a report dict with a "stage" key:
        - "no-pending": nothing to publish (safe no-op, no AI/Graph
          API call at all).
        - "lifecycle": the propose/approve/execute chain raised for
          one platform (report["platform"] says which).
        - "published": both Instagram and Facebook succeeded (this
          run, or on an earlier attempt already checkpointed);
          report["action"] is a {"instagram": id, "facebook": id}
          dict. The pending record has moved to
          published_visual_content so a later run never reposts
          either platform.
        - "failed": one platform's Graph API call itself reported
          failure (report["platform"] says which; report["action"]
          is that platform's own failed action) -- the pending record
          is deliberately left in place, with any already-succeeded
          platform's action id checkpointed in it
          (report["platform_actions"]), so a later run retries only
          the platform that failed rather than reposting to one that
          already worked or re-rendering a brand new image.
        """

        pending = self._oldest_pending()

        if pending is None:
            return {"stage": "no-pending", "caption": None, "image_path": None}

        try:
            payload = json.loads(pending["content"])
        except (ValueError, TypeError):
            # A corrupted/unparseable pending record can never be
            # published -- move it out of the way so it does not
            # block every future run forever, and log why.
            self.memory.move(PENDING_CATEGORY, PUBLISHED_CATEGORY, pending["id"])
            self.memory.remember(
                category="lessons",
                content=(
                    f"Discarded an unparseable pending_visual_content "
                    f"record (id={pending['id']})."
                ),
                memory_type="lesson",
                source="visual-content-error",
                importance=2,
            )
            return {"stage": "no-pending", "caption": None, "image_path": None}

        image_path = payload.get("image_path")
        caption = payload.get("caption", "")
        # Falls back to the plain caption for any pending record saved
        # before ig_caption existed -- never crashes on an older
        # record, just publishes without the hashtag block that time.
        publish_caption = payload.get("ig_caption") or caption
        actions = dict(payload.get("platform_actions") or {})

        try:
            image_url = self._build_image_url(image_path, repo=repo, branch=branch)
        except RuntimeError as exc:
            return {
                "stage": "lifecycle",
                "platform": None,
                "error": str(exc),
                "caption": caption,
                "image_path": image_path,
            }

        for platform, tool_name in self._PLATFORM_TOOLS:
            if actions.get(platform):
                continue

            tool_name = tool_name or self.tool_name

            try:
                proposed = self.lifecycle.propose(
                    tool_name,
                    params={"image_url": image_url, "caption": publish_caption},
                    source="aion",
                )
                approved = self.lifecycle.auto_approve(
                    proposed["id"], policy="visual-safety-style-gate"
                )
                executed = self.lifecycle.execute(approved["id"])
            except Exception as exc:
                return {
                    "stage": "lifecycle",
                    "platform": platform,
                    "error": str(exc),
                    "caption": caption,
                    "image_path": image_path,
                    "platform_actions": actions,
                }

            if executed["status"] != "executed":
                payload["platform_actions"] = actions
                self.memory.update(
                    PENDING_CATEGORY, pending["id"],
                    content=json.dumps(payload, ensure_ascii=False),
                )
                return {
                    "stage": "failed",
                    "platform": platform,
                    "action": executed,
                    "platform_actions": actions,
                    "caption": caption,
                    "image_path": image_path,
                    "image_url": image_url,
                }

            actions[platform] = executed.get("id")
            payload["platform_actions"] = actions
            self.memory.update(
                PENDING_CATEGORY, pending["id"],
                content=json.dumps(payload, ensure_ascii=False),
            )

        self.memory.move(
            PENDING_CATEGORY, PUBLISHED_CATEGORY, pending["id"],
            content=json.dumps(payload, ensure_ascii=False),
        )
        language = payload.get("language", "th")
        if self.social_generator is not None:
            self.social_generator.record_published_language(
                language, "instagram", actions.get("instagram"),
            )
        else:
            # publish_once is independently testable and can be invoked
            # later with no generator object; keep language accounting
            # intact in that valid split-stage configuration.
            self.memory.remember(
                category="social_language_log",
                content=(f"platform=instagram; language={language}; "
                         f"action={actions.get('instagram', 'unknown')}"),
                memory_type="action",
                source="social-language-strategy",
                importance=1,
                tags=[language, "instagram"],
            )
        self.memory.remember(
            category="social_language_log",
            content=(f"platform=facebook; language={language}; "
                     f"action={actions.get('facebook', 'unknown')}"),
            memory_type="action",
            source="social-language-strategy",
            importance=1,
            tags=[language, "facebook"],
        )

        return {
            "stage": "published",
            "action": actions,
            "caption": caption,
            "image_path": image_path,
            "image_url": image_url,
        }
