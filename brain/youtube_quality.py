"""Deterministic quality contract for AION's YouTube uploads.

The gate prevents a technically valid upload from becoming an empty,
interchangeable AI video. It is intentionally conservative and inspectable;
it does not attempt to judge truth from prose alone.
"""

import re

from brain.audience_accessibility import AudienceAccessibilityGate
from brain.channel_policy import ChannelPolicy
from brain.topic_novelty import TopicNoveltyGate


class YouTubeQualityGate:
    """Require an explicit viewer benefit and avoid duplicate uploads."""

    MIN_CAPTION_LENGTH = 60

    @staticmethod
    def _normalise(text):
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

    def __init__(self, root=None):
        self.policy = ChannelPolicy(root)

    def assess(self, payload, prior_payloads=()):
        payload = dict(payload or {})
        caption = str(payload.get("caption") or "").strip()
        viewer_value = str(payload.get("viewer_value") or "").strip()
        video_path = str(payload.get("video_path") or "").strip()
        reasons = []
        if not video_path:
            reasons.append("missing-video-path")
        if len(caption) < self.MIN_CAPTION_LENGTH:
            reasons.append("caption-too-short-to-demonstrate-viewer-value")
        if not viewer_value:
            reasons.append("missing-explicit-viewer-value")
        visual_style = str(payload.get("visual_style") or "").strip()
        required_style = self.policy.production()["automatic_release_visual_style"]
        # Queue preparation is not the final authority: an already-created
        # upload record must also be prevented from bypassing a later brand
        # decision.  This keeps every automatic release on the one current
        # channel signature.
        if visual_style != required_style:
            reasons.append("visual-style-not-channel-signature")

        prior_captions = {self._normalise(item.get("caption")) for item in prior_payloads}
        prior_paths = {str(item.get("video_path") or "").strip() for item in prior_payloads}
        if self._normalise(caption) in prior_captions:
            reasons.append("duplicate-narrative")
        if video_path and video_path in prior_paths:
            reasons.append("duplicate-video")
        if any(TopicNoveltyGate.same_topic(payload, previous) for previous in prior_payloads):
            reasons.append("duplicate-topic")

        # AION's default renderer is illustrated rather than photorealistic.
        # Unknown/realistic sources are never automatically declared safe:
        # retain an explicit review signal in the upload record.
        disclosure_review = visual_style != required_style
        accessibility = AudienceAccessibilityGate().assess(payload)
        return {
            "eligible": not reasons,
            "reasons": reasons,
            "viewer_value": viewer_value,
            "ai_disclosure_review": disclosure_review,
            "audience_accessibility": accessibility,
        }
