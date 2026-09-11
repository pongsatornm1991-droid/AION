"""Deterministic quality contract for AION's YouTube uploads.

The gate prevents a technically valid upload from becoming an empty,
interchangeable AI video. It is intentionally conservative and inspectable;
it does not attempt to judge truth from prose alone.
"""

import re


class YouTubeQualityGate:
    """Require an explicit viewer benefit and avoid duplicate uploads."""

    MIN_CAPTION_LENGTH = 60

    @staticmethod
    def _normalise(text):
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

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

        prior_captions = {self._normalise(item.get("caption")) for item in prior_payloads}
        prior_paths = {str(item.get("video_path") or "").strip() for item in prior_payloads}
        if self._normalise(caption) in prior_captions:
            reasons.append("duplicate-narrative")
        if video_path and video_path in prior_paths:
            reasons.append("duplicate-video")

        # AION's default renderer is illustrated rather than photorealistic.
        # Unknown/realistic sources are never automatically declared safe:
        # retain an explicit review signal in the upload record.
        disclosure_review = payload.get("visual_style") != "illustrated-aion-storyboard-v4"
        return {
            "eligible": not reasons,
            "reasons": reasons,
            "viewer_value": viewer_value,
            "ai_disclosure_review": disclosure_review,
        }
