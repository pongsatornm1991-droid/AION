"""Prepare finished AION Creator episodes for an auditable YouTube upload."""

import json
import os
import re
from pathlib import Path

from brain.autonomy_policy import AutonomyPolicy
from brain.creator_series import CreatorSeriesRegistry
from brain.episode_numbering import EpisodeNumbering
from brain.identity_disclosure import append_identity_disclosure
from brain.visual_story_policy import VisualStoryPolicy
from brain.channel_policy import ChannelPolicy


class YouTubeCreatorQueue:
    """Bridge asset-backed Creator Series episodes to YouTube upload review."""

    CATEGORY = "youtube_creator_queue"
    READY_STATUS = "production-ready-assets-and-script"
    RETIRED_STATUS = "retired-do-not-publish"
    RESEARCH_REJECTED_STATUS = "research-evidence-rejected-preserved"
    # Owner-approved addition, 2026-09-26: the description had no invitation
    # to subscribe at all. A plain, non-manipulative line, not a manufactured
    # urgency hook -- consistent with the channel's own claim-safety stance
    # elsewhere.
    SUBSCRIBE_CTA = "New question, new evidence -- every day. Subscribe to follow along."

    @staticmethod
    def _cover_quality(path, content_kind=None):
        """Verify a readable cover in the aspect ratio used by its release lane.

        Shorts are composed vertically, so a 9:16 cover is valid evidence for
        the Studio/dashboard and may be offered to YouTube. Long-form still
        requires a conventional 16:9 thumbnail.
        """
        try:
            from PIL import Image
            with Image.open(path) as image:
                width, height = image.size
                ratio = width / height if height else 0
                is_vertical_short = content_kind == "short" and abs(ratio - (9 / 16)) <= 0.03 and width >= 720 and height >= 1280
                is_widescreen = width >= 1280 and height >= 720 and abs(ratio - (16 / 9)) <= 0.03
                valid = is_vertical_short or is_widescreen
                return {"eligible": valid, "width": width, "height": height,
                        "reason": None if valid else "cover-must-be-vertical-720x1280-or-widescreen-1280x720"}
        except Exception:
            return {"eligible": False, "width": 0, "height": 0, "reason": "cover-is-not-a-readable-image"}

    @staticmethod
    def _content_kind(episode):
        return "short" if episode.get("format") == "illustrated-narrated-short" else "long-form"

    @classmethod
    def _pipeline_stage(cls, episode, previous, video_exists):
        """One truthful human-facing stage, never a guessed publish status."""
        payload = previous[1] if previous else {}
        if (payload.get("youtube") or {}).get("video_id"):
            return {"id": "published", "label": "เผยแพร่แล้ว"}
        if episode.get("status") == cls.RETIRED_STATUS:
            return {"id": "retired", "label": "ยกเลิกจากคิว"}
        if episode.get("status") == cls.RESEARCH_REJECTED_STATUS:
            return {"id": "research", "label": "เก็บบทเรียนหลักฐาน · ยังไม่ผลิต"}
        if episode.get("status") == "storyboard-ready-needs-assets":
            return {"id": "images", "label": "กำลังสร้างภาพ"}
        if episode.get("status") == "assets-ready-for-assembly":
            return {"id": "assembly", "label": "กำลังประกอบวิดีโอ"}
        gate = payload.get("quality_gate") or {}
        if not video_exists:
            return {"id": "assembly", "label": "กำลังประกอบวิดีโอ"}
        if gate.get("state") == "blocked":
            return {"id": "blocked", "label": "ต้องแก้ตาม Quality Gate"}
        if gate.get("eligible") and payload.get("upload_status") == "authorized-for-aion-publish":
            return {"id": "scheduled", "label": "ผ่าน QA · รอรอบเผยแพร่"}
        return {"id": "quality", "label": "กำลังตรวจ Quality Gate"}

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

    # Small, generic connector words filtered out of the topic when building
    # YouTube search tags -- the goal is keeping the *subject* words
    # ("maps", "google", "cartography"), not full grammatical questions.
    _TAG_STOPWORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "do", "does", "did", "doing", "why", "how", "what", "when", "where",
        "who", "which", "this", "that", "these", "those", "to", "of", "in",
        "on", "for", "and", "or", "but", "with", "from", "into", "than",
        "as", "it", "its", "their", "they", "them", "we", "you", "your",
        "can", "could", "would", "will", "not", "no", "so", "if", "about",
        "than", "then", "there", "here", "one", "some", "any", "more",
    }

    @classmethod
    def _topic_and_keywords(cls, payload):
        """The raw topic string plus its subject keywords, stopwords removed.

        Shared by _video_tags() and _title_hashtag() so both always agree on
        what the actual subject of an episode is.
        """
        topic = str(payload.get("topic_key") or payload.get("title") or "").strip()
        words = re.findall(r"[a-z][a-z'-]+", topic.lower())
        seen, keywords = set(), []
        for word in words:
            if len(word) < 3 or word in cls._TAG_STOPWORDS or word in seen:
                continue
            seen.add(word)
            keywords.append(word)
        return topic, keywords

    @classmethod
    def _video_tags(cls, payload, is_short):
        """Real, topic-specific YouTube search tags for one upload.

        Every prior upload sent none at all (found 2026-09-26): the
        snippet's `tags` field is a direct discovery signal YouTube uses to
        match a video to a search, and it was empty on every single Creator
        episode. This never overrides a human's own judgement about a
        video -- it only gives the upload the same keyword metadata any
        deliberately-optimized YouTube video already carries.
        """
        topic, keywords = cls._topic_and_keywords(payload)
        tags = []
        if topic:
            tags.append(topic[:100])
        tags.extend(keywords[:8])
        tags.extend(["AION", "Wait How", "education", "curiosity"])
        if is_short:
            tags.append("Shorts")
        final, seen_lower = [], set()
        for tag in tags:
            key = tag.strip().lower()
            if not key or key in seen_lower:
                continue
            seen_lower.add(key)
            final.append(tag.strip())
        return final

    @classmethod
    def _title_hashtag(cls, payload):
        """One relevant, capitalized hashtag for a Short's on-screen title.

        Uses only the episode's own subject keywords -- never the fixed
        channel/format tags _video_tags() also adds ("education" and
        "curiosity" are themselves plain lowercase words, so scanning
        _video_tags()'s combined output for the first lowercase entry would
        wrongly grab one of those on a topic with no surviving keyword).
        Owner-reviewed competitor scan, 2026-09-27: Kurzgesagt (25M subs)
        ships zero hashtags in its titles, but both direct same-niche
        comparables close to AION's own scale do, and YouTube surfaces up
        to a title's first 3 hashtags as clickable topic chips above a
        Short -- real extra discovery surface a very small channel should
        not skip. Kept to a single tag so the hook itself stays dominant.
        """
        _, keywords = cls._topic_and_keywords(payload)
        return f"#{keywords[0].capitalize()}" if keywords else None

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
        # One episode currently failing a content-policy check must not hide
        # every other candidate from release-readiness/queue computation --
        # see brain/creator_series.py's episodes(skip_invalid=True) docstring.
        for episode in CreatorSeriesRegistry(self.root).episodes(skip_invalid=True):
            video_path = self.root / "content" / "reels" / f"{episode['id']}.mp4"
            subtitle_path = self.root / "content" / "reels" / f"{episode['id']}.srt"
            ready = episode.get("status") == self.READY_STATUS and video_path.is_file()
            content_kind = self._content_kind(episode)
            release_blockers = []
            # Reject an outdated storyboard before it ever occupies a release
            # slot. Video QA still inspects the rendered file later, but this
            # prevents legacy 25/36-second Shorts from blocking a complete one.
            if content_kind == "short":
                if int(episode.get("target_duration_seconds") or 0) < VisualStoryPolicy.MIN_SHORT_DURATION_SECONDS:
                    release_blockers.append("short-must-be-at-least-50-seconds")
                if len(episode.get("scenes") or []) < VisualStoryPolicy.MIN_SHORT_SCENES:
                    release_blockers.append("short-must-have-at-least-10-scenes")
                if int(episode.get("scene_seconds") or 0) != VisualStoryPolicy.MIN_SCENE_SECONDS:
                    release_blockers.append("short-scenes-must-be-5-seconds")
            # Style lock: an episode may only enter the release queue once a
            # human/Studio has explicitly marked its visual style approved.
            # This is opt-in on purpose -- silence is never approval -- so a
            # one-off experimental style (or an "urgent" special release that
            # skips the normal queue order) can never win an automatic slot
            # just by existing. This is what let an old-style urgent special
            # release get published ahead of correctly styled new work; a
            # historical episode already published is unaffected, since this
            # only gates new entries to the upload-ready queue.
            visual_style = episode.get("visual_style") or {}
            if visual_style.get("approved") is not True:
                release_blockers.append("visual-style-not-approved-for-release")
            # Approval alone protects experimentation, but the automatic
            # daily lane must also preserve the one signature the owner has
            # selected for the channel. A different approved style can still
            # exist as an archive or deliberate future decision; it cannot
            # silently consume a routine Wait, How? release appointment.
            if visual_style.get("id") != ChannelPolicy(self.root).production()["automatic_release_visual_style"]:
                release_blockers.append("visual-style-not-channel-signature")
            visual_qa = episode.get("visual_qa") or {}
            if visual_qa.get("eligible") is not True:
                release_blockers.append("visual-asset-qa-not-passed")
            # An incident record (e.g. "narration ends before the final
            # scene") must block release on its own facts, never on whether
            # someone also remembered to spell a matching `status` value.
            # Found 2026-09-22: an episode's own status
            # ("quality-blocked-story-and-audio") happened not to match
            # READY_STATUS, which was the *only* reason it was never
            # offered for release -- an accident of spelling, not an
            # enforced gate. A later status edit (or a differently-named
            # incident) would have slipped straight through. Set
            # quality_incident.state to anything other than "blocked" (or
            # remove the block) once the episode has genuinely been
            # rebuilt; the historical reasons/action can stay on file
            # either way as an audit record.
            if (episode.get("quality_incident") or {}).get("state") == "blocked":
                release_blockers.append("unresolved-quality-incident")
            # Same class of gap, found the same day while auditing every
            # status value actually in use: Research can return a staged
            # draft with `status: "research-returned-source-integrity"`
            # plus a `return_reason` (e.g. sources that are not
            # independent/traceable enough), and nothing enforced that
            # either -- it was safe only because that status string also
            # doesn't match READY_STATUS. Enforced explicitly for the same
            # reason: a later status edit must not silently un-quarantine
            # a draft Research already rejected.
            if episode.get("status") == "research-returned-source-integrity":
                release_blockers.append("returned-for-insufficient-source-integrity")
            # A recovery attempt can also stop before it has enough on-topic
            # evidence.  Keep that draft and its findings for future research,
            # but enforce its no-release boundary explicitly.  It must never
            # become publishable merely because a later edit changes a status
            # string or happens to add a local video file.
            if episode.get("status") == self.RESEARCH_REJECTED_STATUS:
                release_blockers.append("preserved-for-future-evidence-research")
            retired = episode.get("status") == self.RETIRED_STATUS
            previous = recorded.get(episode["id"])
            stage = self._pipeline_stage(episode, previous, video_path.is_file())
            result.append({
                "episode_id": episode["id"],
                "content_kind": content_kind,
                "format": episode.get("format", "long-form-illustrated"),
                "title": episode["title"],
                "episode_number": episode.get("episode_number"),
                "display_title": EpisodeNumbering.display_title(
                    episode["title"], episode.get("episode_number")
                ),
                "status": "retired" if retired else ("published" if previous and (previous[1].get("youtube") or {}).get("video_id") else "already-prepared" if previous else (
                    "upload-ready" if ready and not release_blockers else "needs-production"
                )),
                "pipeline_stage": stage,
                "release_eligible": not retired and not release_blockers,
                "release_blockers": release_blockers,
                "video_path": str(video_path.relative_to(self.root)).replace("\\", "/"),
                "video_exists": video_path.is_file(),
                "cover_path": f"content/reels/{episode['id']}-cover.png",
                "cover_exists": (self.root / "content" / "reels" / f"{episode['id']}-cover.png").is_file(),
                "cover_quality": self._cover_quality(self.root / "content" / "reels" / f"{episode['id']}-cover.png", content_kind),
                "subtitle_path": str(subtitle_path.relative_to(self.root)).replace("\\", "/"),
                "subtitle_exists": subtitle_path.is_file(),
                "audience_promise": episode["audience_promise"],
                "uncertainty_boundary": (
                    episode.get("science_boundary")
                    or episode.get("history_boundary")
                    or episode.get("uncertainty_boundary")
                ),
                "source_count": len(episode.get("sources") or []),
                "caption": self._caption(episode),
                "topic_key": episode.get("topic_key") or episode.get("wonder_hook") or episode.get("title"),
                "story_package_id": episode.get("story_package_id"),
                "content_angle_key": episode.get("content_angle_key"),
                "release_priority": (episode.get("special_release") or {}).get("release_priority", "normal"),
                # A corrective release may replace precisely one named AION
                # episode.  This is not a general duplicate bypass: the
                # source storyboard must declare the predecessor explicitly.
                "supersedes_episode_id": (episode.get("special_release") or {}).get("supersedes_episode_id"),
                "source_urls": [source.get("url") for source in (episode.get("sources") or []) if source.get("url")],
                "viewer_value": episode["audience_promise"],
                "visual_style": (episode.get("visual_style") or {}).get("id") or VisualStoryPolicy.CHANNEL_VISUAL_STYLE,
                "visual_qa": episode.get("visual_qa"),
                # Queue state is durable and is the source of truth for the
                # UI.  Keep the friendly display status above for legacy
                # screens, but never discard the authorization state.
                "publication_status": previous[1].get("upload_status") if previous else None,
                "video_qa": (((previous[1].get("youtube") or {}).get("quality") or {}).get("video_qa") if previous else None),
                # Preserve the last gate decision even when an upload was
                # blocked.  A blocked item is useful operational evidence,
                # not a reason for the dashboard to become silent.
                "quality_gate": previous[1].get("quality_gate") if previous else None,
            })
        return result

    def prepare_once(self, content_kind=None, episode_id=None):
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

        # An episode may have been authorized before Studio finished its
        # cover or before its corrective-release metadata was added.  Refresh
        # that one durable record from the source episode instead of leaving
        # it permanently blocked as "missing-cover".  This is metadata-only:
        # it never uploads, changes credentials, or broadens authorization.
        records = self._records_by_episode()
        for candidate in self.candidates():
            if content_kind and candidate.get("content_kind") != content_kind:
                continue
            if episode_id and candidate.get("episode_id") != episode_id:
                continue
            existing = records.get(candidate["episode_id"])
            if existing is None:
                continue
            entry, payload = existing
            # A record that has already been fully prepared must not keep
            # winning this pass forever: that used to leave later completed
            # episodes invisible behind the first queued one.  Refresh only
            # genuinely incomplete legacy metadata, then let the next
            # eligible episode enter the queue.
            if (payload.get("upload_status") != "authorized-for-aion-publish"
                    or (payload.get("youtube") or {}).get("video_id")
                    or (payload.get("cover_path") and payload.get("subtitle_path"))):
                continue
            refreshed = {
                **payload,
                **candidate,
                "upload_status": "authorized-for-aion-publish",
                "publish_note": payload.get("publish_note") or (
                    "AION is authorized to publish after the quality gate and channel checks pass."
                ),
            }
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(refreshed, ensure_ascii=False))
            return {"stage": "authorized-for-publishing", "refreshed": True, "record": entry, **refreshed}
        eligible = [item for item in self.candidates()
                    if item["status"] == "upload-ready"
                    and item.get("release_eligible")
                    and (not content_kind or item.get("content_kind") == content_kind)
                    and (not episode_id or item.get("episode_id") == episode_id)]
        # A documented corrective release may go first, but it can never
        # bypass the normal quality gates below. This prevents a stale ready
        # file from winning merely because its filename sorts earlier.
        eligible.sort(key=lambda item: (item.get("release_priority") != "urgent", item.get("episode_id") or ""))
        candidate = eligible[0] if eligible else None
        if candidate is None:
            return {"stage": "no-upload-ready-creator-episode"}
        # The number is allocated only once a new episode reaches release
        # preparation.  Drafts cannot consume numbers and old videos retain
        # their historic titles.
        candidate = {**candidate, **EpisodeNumbering(self.root).assign(candidate)}
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
        from brain.work_queue import WorkQueue
        work = WorkQueue(self.memory).ensure(
            "studio-to-youtube", candidate["episode_id"], "Video QA Agent", candidate["display_title"],
            "YouTube Publishing Agent", status="ready", related=[record.get("id")] if record.get("id") else [],
            priority="urgent",
        )
        return {"stage": "authorized-for-publishing" if autonomous else "prepared-for-review", "record": record, **payload}

    def quality_pending(self, content_kind=None, episode_id=None):
        """Run the complete local Quality Gate for queued, unuploaded episodes.

        This is deliberately separate from publishing.  It gives the release
        buffer an auditable answer before a scheduled slot arrives, while the
        publish step repeats the same checks immediately before it contacts
        YouTube.  No account, video privacy, or external platform is changed.
        """
        if self.memory is None:
            raise ValueError("Memory is required to quality-check a creator episode.")
        records = self._records_by_episode()
        checked, passed, blocked = [], [], []
        from brain.youtube_quality import YouTubeQualityGate
        from brain.video_quality import VideoQualityGate
        for entry, payload in records.values():
            if payload.get("upload_status") != "authorized-for-aion-publish":
                continue
            if (payload.get("youtube") or {}).get("video_id"):
                continue
            if content_kind and payload.get("content_kind") != content_kind:
                continue
            if episode_id and payload.get("episode_id") != episode_id:
                continue
            prior = [record for _, record in records.values()
                     if (record.get("youtube") or {}).get("video_id")
                     and record.get("episode_id") != payload.get("supersedes_episode_id")]
            quality = YouTubeQualityGate().assess(payload, prior)
            video_quality = VideoQualityGate(self.root).assess(
                payload.get("video_path"), payload.get("content_kind") or "short"
            )
            if payload.get("content_kind") == "long-form" and not (self.root / str(payload.get("subtitle_path") or "")).is_file():
                video_quality["eligible"] = False
                video_quality["reasons"] = list(video_quality.get("reasons") or []) + ["missing-caption-track"]
            quality["video_qa"] = video_quality
            if not video_quality["eligible"]:
                quality["eligible"] = False
                quality["reasons"] = list(quality.get("reasons") or []) + [
                    f"video-qa:{item}" for item in video_quality["reasons"]
                ]
            updated = {
                **payload,
                "quality_gate": {
                    "state": "passed" if quality["eligible"] else "blocked",
                    "eligible": bool(quality["eligible"]),
                    "reasons": list(quality.get("reasons") or []),
                },
                # Keep the detailed technical inspection adjacent to the
                # queue record so the dashboard can explain a block.
                "quality_review": quality,
            }
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
            checked.append(payload.get("episode_id"))
            (passed if quality["eligible"] else blocked).append(payload.get("episode_id"))
        return {"stage": "quality-gate-complete", "checked": checked, "passed": passed, "blocked": blocked}

    def reconcile_owner_confirmed_publication(self, episode_id, video_id, url):
        """Record an already-public video when an earlier delivery lost its audit entry.

        This deliberately does *not* call YouTube.  It is a narrow recovery
        path for a channel owner to reconcile a known publication with the
        durable Studio queue, preventing Studio from offering the same video
        for upload again.
        """
        if self.memory is None:
            raise ValueError("Memory is required to reconcile a creator episode.")
        episode_id = str(episode_id or "").strip()
        video_id = str(video_id or "").strip()
        url = str(url or "").strip()
        if not episode_id or not video_id or not url:
            raise ValueError("episode_id, video_id, and url are required.")

        candidate = next((item for item in self.candidates()
                          if item.get("episode_id") == episode_id), None)
        if candidate is None:
            raise ValueError(f"Creator episode not found: {episode_id}")
        records = self._records_by_episode()
        existing = records.get(episode_id)
        prior = existing[1] if existing else {}
        payload = {
            **prior,
            **candidate,
            "upload_status": "published",
            "publication_status": "published",
            "youtube": {
                **(prior.get("youtube") or {}),
                "video_id": video_id,
                "url": url,
                "privacy_status": "public",
                "verification": "owner-confirmed-manual-reconciliation",
            },
            "publish_note": (
                "Owner-confirmed reconciliation: the public YouTube video existed, "
                "but its prior delivery did not persist a Studio queue record. "
                "No upload or privacy change was performed by this reconciliation."
            ),
        }
        if existing:
            entry = self.memory.update(self.CATEGORY, existing[0]["id"], content=json.dumps(payload, ensure_ascii=False))
        else:
            entry = self.memory.remember(
                self.CATEGORY, json.dumps(payload, ensure_ascii=False),
                memory_type="action", source="aion-owner-publication-reconciliation", importance=4,
                tags=["youtube", "creator-series", episode_id, "owner-confirmed"],
            )
        return {"stage": "reconciled-published", "record": entry, **payload}

    def publish_once(self, uploader=None, content_kind=None, episode_id=None):
        """Upload one authorized Creator episode exactly once."""
        if self.memory is None:
            raise ValueError("Memory is required to publish a creator episode.")
        if not AutonomyPolicy(self.root).public_publishing_enabled:
            return {"stage": "owner-policy-required"}
        target = next((item for item in self._records_by_episode().values()
                       if item[1].get("upload_status") == "authorized-for-aion-publish"
                       and (not content_kind or item[1].get("content_kind") == content_kind)
                       and (not episode_id or item[1].get("episode_id") == episode_id)
                       and not (item[1].get("youtube") or {}).get("video_id")), None)
        if target is None:
            return {"stage": "no-authorized-creator-episode"}
        entry, payload = target
        from brain.work_queue import WorkQueue
        work_queue = WorkQueue(self.memory)
        work_card = work_queue.ensure(
            "studio-to-youtube", payload.get("episode_id"), "YouTube Publishing Agent",
            payload.get("title") or "AION Creator episode", "Audience & Growth", status="ready",
            related=[entry.get("id")] if entry.get("id") else [], priority="urgent",
        )["card"]
        work_queue.transition(
            work_card["task_id"], "in-progress", owner="YouTube Publishing Agent",
            next_owner="Audience & Growth", detail="กำลังตรวจไฟล์และส่งขึ้น YouTube",
        )
        # Records created before caption support did not store subtitle_path.
        # The file convention is stable, so repair that metadata in memory
        # rather than falsely treating a complete episode as missing captions.
        if not payload.get("subtitle_path") and payload.get("episode_id"):
            payload = {
                **payload,
                "subtitle_path": f"content/reels/{payload['episode_id']}.srt",
            }
        path = self.root / str(payload.get("video_path") or "")
        if not path.is_file():
            work_queue.transition(work_card["task_id"], "waiting", owner="Studio", next_owner="Video QA Agent", detail="รอไฟล์วิดีโอเดิมจาก Studio")
            return {"stage": "missing-video", "episode_id": payload.get("episode_id")}
        cover_path = self.root / str(payload.get("cover_path") or "")
        if not cover_path.is_file():
            work_queue.transition(work_card["task_id"], "waiting", owner="Studio", next_owner="Video QA Agent", detail="รอภาพปกที่ตรวจสอบได้ก่อนเผยแพร่")
            return {"stage": "missing-cover", "episode_id": payload.get("episode_id")}
        cover_quality = self._cover_quality(cover_path, payload.get("content_kind"))
        if not cover_quality["eligible"]:
            work_queue.transition(work_card["task_id"], "waiting", owner="Studio", next_owner="Video QA Agent", detail="ภาพปกไม่ผ่านขนาดหรืออ่านไฟล์ไม่ได้ จึงไม่เผยแพร่")
            return {"stage": "invalid-cover", "episode_id": payload.get("episode_id"), "cover_quality": cover_quality}
        records = self._records_by_episode()
        superseded_id = str(payload.get("supersedes_episode_id") or "").strip()
        prior = [record for _, record in records.values()
                 if (record.get("youtube") or {}).get("video_id")
                 and record.get("episode_id") != superseded_id]
        from brain.youtube_quality import YouTubeQualityGate
        quality = YouTubeQualityGate().assess(payload, prior)
        from brain.video_quality import VideoQualityGate
        video_quality = VideoQualityGate(self.root).assess(payload.get("video_path"), payload.get("content_kind") or "short")
        if payload.get("content_kind") == "long-form" and not (self.root / str(payload.get("subtitle_path") or "")).is_file():
            video_quality["eligible"] = False
            video_quality["reasons"] = list(video_quality.get("reasons") or []) + ["missing-caption-track"]
        quality["video_qa"] = video_quality
        if not video_quality["eligible"]:
            quality["eligible"] = False
            quality["reasons"] = list(quality.get("reasons") or []) + [f"video-qa:{item}" for item in video_quality["reasons"]]
        if not quality["eligible"]:
            blocked = {
                **payload,
                "quality_gate": {
                    "state": "blocked",
                    "eligible": False,
                    "reasons": list(quality.get("reasons") or []),
                },
            }
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(blocked, ensure_ascii=False))
            work_queue.transition(work_card["task_id"], "waiting", owner="Video QA Agent", next_owner="Studio", detail="Quality Gate ส่งกลับรายการเดิมเพื่อแก้ไข")
            return {"stage": "quality-review-required", "episode_id": payload.get("episode_id"), **quality}

        # A replacement is allowed only after its named predecessor is made
        # private.  This keeps the public channel free of duplicate stories
        # and never touches an arbitrary video outside AION's durable queue.
        replacement = None
        if superseded_id:
            predecessor = records.get(superseded_id)
            if predecessor is None:
                return {"stage": "replacement-predecessor-not-found", "episode_id": payload.get("episode_id")}
            previous_entry, previous_payload = predecessor
            previous_youtube = dict(previous_payload.get("youtube") or {})
            previous_video_id = str(previous_youtube.get("video_id") or "").strip()
            if not previous_video_id:
                return {"stage": "replacement-predecessor-not-published", "episode_id": payload.get("episode_id")}
            if previous_youtube.get("privacy_status") != "private":
                try:
                    from tools.youtube import set_video_privacy
                    privacy_result = set_video_privacy(previous_video_id, "private")
                except Exception as exc:
                    error = str(exc).strip() or type(exc).__name__
                    work_queue.transition(work_card["task_id"], "waiting", owner="YouTube Publishing Agent", next_owner="YouTube Publishing Agent", detail="เปลี่ยนคลิปเดิมเป็นส่วนตัวไม่สำเร็จ จึงยังไม่ปล่อยคลิปทดแทน")
                    return {"stage": "replacement-privacy-update-failed", "episode_id": payload.get("episode_id"), "error": error}
                previous_updated = {
                    **previous_payload,
                    "youtube": {**previous_youtube, **privacy_result},
                    "upload_status": "superseded-private",
                    "superseded_by": payload.get("episode_id"),
                }
                self.memory.update(self.CATEGORY, previous_entry["id"], content=json.dumps(previous_updated, ensure_ascii=False))
                replacement = {"episode_id": superseded_id, "video_id": previous_video_id, "privacy_status": "private"}
        technical = video_quality.get("technical") or {}
        video_ratio = (technical.get("width", 0) / technical.get("height", 1)) if technical.get("height") else 0
        is_youtube_short = (
            payload.get("content_kind") == "short"
            or (abs(video_ratio - (9 / 16)) <= 0.04 and technical.get("duration_seconds", 0) <= 180)
        )
        format_tags = "#Shorts #AION #AI" if is_youtube_short else "#AION #AI"
        description = "\n\n".join(part for part in (
            payload.get("caption"),
            self.SUBSCRIBE_CTA,
            append_identity_disclosure("", "youtube"),
            format_tags,
        ) if part)
        # The public title omits the internal "EP. NNN —" numbering: a cold
        # viewer arriving from search doesn't know what episode of what they
        # found, and it pushes the actual hook further from the start of the
        # title. display_title (with the prefix) remains what the Operations
        # dashboard and internal work-queue show. Owner-approved change,
        # 2026-09-26, after the two highest-performing videos on the channel
        # both used a bare "How X..." title with no such prefix.
        public_title = str(payload.get("title") or payload.get("display_title") or "AION Wonders")
        if is_youtube_short:
            hashtag = self._title_hashtag(payload)
            if hashtag and len(public_title) + 1 + len(hashtag) <= 100:
                public_title = f"{public_title} {hashtag}"
        video_tags = self._video_tags(payload, is_youtube_short)
        try:
            if uploader is None:
                from tools.youtube import upload_short
                uploader = upload_short
                result = uploader(str(path), public_title, description,
                                  privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "public"),
                                  thumbnail_path=str(cover_path), tags=video_tags)
            else:
                result = uploader(str(path), public_title, description)
        except Exception as exc:
            # Some provider exceptions have an empty string representation.
            # Preserve their type so the Dashboard and retry log never show a
            # blank, un-actionable failure.
            error = str(exc).strip() or type(exc).__name__
            work_queue.transition(work_card["task_id"], "waiting", owner="YouTube Publishing Agent", next_owner="YouTube Publishing Agent", detail="อัปโหลดไม่สำเร็จชั่วคราว: เก็บงานเดิมไว้ retry")
            return {"stage": "upload-failed", "episode_id": payload.get("episode_id"), "error": error}
        if result.get("privacy_status") != "public":
            # The upload call can succeed while the video stays private
            # (for example a manual run whose environment never set
            # YOUTUBE_PRIVACY_STATUS). Never report "published" on trust
            # alone: try once to correct it, then tell the truth about
            # whatever the final state actually is.
            try:
                from tools.youtube import set_video_privacy
                result = {**result, **set_video_privacy(result["video_id"], "public")}
            except Exception as exc:
                result = {**result, "privacy_release_error": str(exc).strip() or type(exc).__name__}
        if result.get("privacy_status") != "public":
            not_public = {
                **payload,
                "youtube": {**result, "quality": quality},
                "quality_gate": {"state": "passed", "eligible": True, "reasons": []},
                "upload_status": "uploaded-not-public",
            }
            self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(not_public, ensure_ascii=False))
            work_queue.transition(work_card["task_id"], "waiting", owner="YouTube Publishing Agent", next_owner="YouTube Publishing Agent", detail="อัปโหลดสำเร็จแต่ยังไม่เป็นสาธารณะ ต้องแก้ไขก่อนถือว่าเผยแพร่แล้ว")
            return {"stage": "uploaded-but-not-public", "episode_id": payload.get("episode_id"), **result}
        updated = {
            **payload,
            "youtube": {**result, "quality": quality},
            "quality_gate": {"state": "passed", "eligible": True, "reasons": []},
            "upload_status": "published",
        }
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
        self.memory.remember(
            "social_language_log",
            f"platform=youtube-creator; episode={updated.get('episode_id')}; video={result.get('video_id', 'unknown')}",
            memory_type="action", source="aion-youtube-creator-publish", importance=1,
            tags=["youtube", "creator-series", updated.get("episode_id", "unknown")],
        )
        work_queue.transition(work_card["task_id"], "completed", owner="Audience & Growth", next_owner="Learning Lab", detail="YouTube ยืนยันการเผยแพร่แล้ว ส่งผลให้ฝ่ายวิเคราะห์")
        return {"stage": "published", "episode_id": updated.get("episode_id"), "replacement": replacement, **result}

    def release_private_once(self, releaser=None):
        """Release one previously quality-gated private AION upload.

        Old videos may have been uploaded while the channel default was
        private.  This is an idempotent, narrowly-scoped recovery: it only
        changes a recorded AION video from private to public after its saved
        Quality Gate has passed.  It never touches arbitrary channel videos.
        """
        if self.memory is None:
            raise ValueError("Memory is required to release a creator episode.")
        if not AutonomyPolicy(self.root).public_publishing_enabled:
            return {"stage": "owner-policy-required"}
        target = next((item for item in self._records_by_episode().values()
                       if (item[1].get("youtube") or {}).get("video_id")
                       and (item[1].get("youtube") or {}).get("privacy_status") == "private"
                       and ((item[1].get("youtube") or {}).get("quality") or {}).get("eligible") is True), None)
        if target is None:
            return {"stage": "no-quality-gated-private-creator-episode"}
        entry, payload = target
        youtube = dict(payload.get("youtube") or {})
        try:
            if releaser is None:
                from tools.youtube import set_video_privacy
                releaser = set_video_privacy
            result = releaser(youtube["video_id"], "public")
        except Exception as exc:
            error = str(exc).strip() or type(exc).__name__
            return {"stage": "release-failed", "episode_id": payload.get("episode_id"), "error": error}
        updated = {**payload, "youtube": {**youtube, **result}}
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
        return {"stage": "released-public", "episode_id": updated.get("episode_id"), **result}

    def audit_existing(self, episode_id=None):
        """Attach a retrospective Video QA report to one already-published episode.

        This only updates AION's local audit record; it never edits the remote
        YouTube upload or contacts an external account.
        """
        if self.memory is None:
            raise ValueError("Memory is required to audit a creator episode.")
        candidates = self._records_by_episode().values()
        target = next((item for item in candidates
                       if (not episode_id or item[1].get("episode_id") == episode_id)
                       and (item[1].get("youtube") or {}).get("video_id")), None)
        if target is None:
            return {"stage": "no-published-creator-episode"}
        entry, payload = target
        from brain.video_quality import VideoQualityGate
        report = VideoQualityGate(self.root).assess(payload.get("video_path"))
        youtube = dict(payload.get("youtube") or {})
        quality = dict(youtube.get("quality") or {})
        quality["video_qa"] = report
        updated = {**payload, "youtube": {**youtube, "quality": quality}}
        self.memory.update(self.CATEGORY, entry["id"], content=json.dumps(updated, ensure_ascii=False))
        return {"stage": "video-qa-recorded", "episode_id": payload.get("episode_id"), "video_qa": report}
