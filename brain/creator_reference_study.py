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
        if parsed.netloc.lower() in {"youtu.be", "www.youtu.be"}:
            return parsed.path.strip("/").split("/", 1)[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
        return (parse_qs(parsed.query).get("v") or [""])[0]

    def _references(self):
        try:
            return json.loads(self.reference_path.read_text(encoding="utf-8")).get("references") or []
        except (OSError, ValueError, TypeError):
            return []

    def _studied_reference_ids(self):
        """Return ids represented by either legacy single or batch studies."""
        studied = set()
        for entry in self.memory.all(self.CATEGORY):
            try:
                record = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            reference = record.get("reference") or {}
            if reference.get("id"):
                studied.add(reference["id"])
            for reference in record.get("references") or []:
                if reference.get("id"):
                    studied.add(reference["id"])
        return studied

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

    def study_all_pending(self, limit=7):
        """Synthesize all pending references with one metadata and one model call.

        This is intentionally a comparative, metadata-only pass. It avoids a
        costly model call per link while preserving an auditable record of the
        references that informed the resulting original AION craft rules.
        """
        limit = max(1, int(limit))
        studied_ids = self._studied_reference_ids()
        targets = [item for item in self._references() if item.get("id") not in studied_ids][:limit]
        if not targets:
            return {"stage": "all-studied", "studied": 0, "reports": []}

        target_video_ids = []
        invalid = []
        for target in targets:
            video_id = self._video_id(target.get("url"))
            if video_id:
                target_video_ids.append((target, video_id))
            else:
                invalid.append(target.get("id"))
        if not target_video_ids:
            return {"stage": "invalid-reference", "studied": 0, "references": invalid, "reports": []}

        try:
            metadata = self.metadata_fn([video_id for _, video_id in target_video_ids])
        except RuntimeError as exc:
            stage = "configuration-needed" if "YOUTUBE_DATA_API_KEY" in str(exc) else "metadata-failed"
            return {"stage": stage, "studied": 0, "references": [item.get("id") for item in targets], "error": str(exc), "reports": []}

        metadata_by_id = {item.get("video_id"): item for item in metadata}
        available = []
        unavailable = list(invalid)
        for target, video_id in target_video_ids:
            item = metadata_by_id.get(video_id)
            if item:
                # Keep the model input deliberately compact and predictable.
                available.append({
                    "reference": target,
                    "metadata": {
                        "title": item.get("title", ""),
                        "channel": item.get("channel", ""),
                        "description": str(item.get("description", ""))[:400],
                        "duration": item.get("duration", ""),
                    },
                })
            else:
                unavailable.append(target.get("id"))
        if not available:
            return {"stage": "metadata-unavailable", "studied": 0, "references": unavailable, "reports": []}

        prompt = "\n".join([
            "Study this user-curated set of creator references for AION's ORIGINAL work.",
            "Use only the supplied public metadata. Do not infer unseen scenes, quote, summarize, copy, imitate, or identify individual creators.",
            "Synthesize exactly five concise, transferable AION production principles. Each must be an original instruction usable across many stories.",
            "Public metadata set:", json.dumps(available, ensure_ascii=False),
        ])
        try:
            principles = self.provider.generate(prompt).strip()
        except Exception as exc:
            return {"stage": "draft-failed", "studied": 0, "references": [item["reference"].get("id") for item in available], "error": str(exc), "reports": []}

        references = [item["reference"] for item in available]
        source = f"{self.SOURCE_PREFIX}batch:{','.join(item.get('id', '') for item in references)}"
        record = {
            "references": references,
            "metadata": available,
            "principles": principles,
            "epistemic_status": "Batch craft notes derived from public metadata only; they are not a reconstruction, summary, or imitation of any reference video.",
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True),
            memory_type="lesson", source=source, importance=3,
            tags=["creator", "craft-study", "originality", "batch"],
        )
        return {
            "stage": "batch-complete", "studied": len(references) if saved.get("saved") else 0,
            "references": [item.get("id") for item in references], "unavailable": unavailable,
            "principles": principles, "reports": [],
        }
