"""Turn user-curated creator references into original craft lessons."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class CreatorReferenceStudy:
    CATEGORY = "creator_reference_studies"
    SOURCE_PREFIX = "aion-creator-reference:"

    def __init__(self, memory, provider, metadata_fn=None, reference_path=None):
        self.memory = memory
        self.provider = provider
        if metadata_fn is None:
            from tools.youtube_discovery import get_youtube_video_metadata
            metadata_fn = get_youtube_video_metadata
        self.metadata_fn = metadata_fn
        self.reference_path = Path(reference_path or Path(__file__).resolve().parents[1] / "assets" / "creator-reference-videos.json")

    @staticmethod
    def _video_id(url):
        parsed = urlparse(str(url))
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
        return (parse_qs(parsed.query).get("v") or [""])[0]

    def _references(self):
        try:
            return json.loads(self.reference_path.read_text(encoding="utf-8")).get("references") or []
        except (OSError, ValueError, TypeError):
            return []

    def study_once(self):
        references = self._references()
        done = {entry.get("source") for entry in self.memory.all(self.CATEGORY)}
        target = next((item for item in references if f"{self.SOURCE_PREFIX}{item.get('id')}" not in done), None)
        if target is None:
            return {"stage": "all-studied", "studied": False}
        video_id = self._video_id(target.get("url"))
        if not video_id:
            return {"stage": "invalid-reference", "studied": False, "reference": target.get("id")}
        try:
            metadata = self.metadata_fn([video_id])
        except RuntimeError as exc:
            stage = "configuration-needed" if "YOUTUBE_DATA_API_KEY" in str(exc) else "metadata-failed"
            return {"stage": stage, "studied": False, "reference": target.get("id"), "error": str(exc)}
        item = next((entry for entry in metadata if entry.get("video_id") == video_id), None)
        if not item:
            return {"stage": "metadata-unavailable", "studied": False, "reference": target.get("id")}
        prompt = "\n".join([
            "Study a user-curated creator reference for AION's ORIGINAL work.",
            "Use only the supplied public metadata. Do not infer unseen scenes, quote, summarize, copy, or imitate the video's protected expression.",
            "Return exactly three concise transferable craft principles, each phrased as an original AION production instruction.",
            "Metadata:", json.dumps(item, ensure_ascii=False),
        ])
        try:
            principles = self.provider.generate(prompt).strip()
        except Exception as exc:
            return {"stage": "draft-failed", "studied": False, "reference": target.get("id"), "error": str(exc)}
        source = f"{self.SOURCE_PREFIX}{target.get('id')}"
        record = {"reference": target, "metadata": item, "principles": principles,
                  "epistemic_status": "Craft notes derived from public metadata only; they are not a reconstruction or summary of the reference video."}
        saved = self.memory.remember(self.CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True),
                                     memory_type="lesson", source=source, importance=3,
                                     tags=["creator", "craft-study", "originality"])
        return {"stage": "studied", "studied": bool(saved.get("saved")), "reference": target.get("id"), "principles": principles}
