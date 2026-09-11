"""Turn one AION story core into platform-native public copy."""

import hashlib
import re


class ContentRouter:
    """A deterministic router: same truth, different platform job."""

    @staticmethod
    def _is_thai(text):
        return bool(re.search(r"[\u0E00-\u0E7F]", str(text or "")))

    def route(self, story, viewer_value):
        story = str(story or "").strip()
        viewer_value = str(viewer_value or "").strip()
        thai = self._is_thai(story)
        facebook_context = (
            "AION กำลังบันทึกคำถามนี้ไว้เพื่อคุยต่อกับทุกคน" if thai
            else "AION is keeping this question open for a wider conversation"
        )
        youtube_label = "สิ่งที่ผู้ชมจะได้: " if thai else "What viewers can take from this: "
        content_id = hashlib.sha256(f"{story}\n{viewer_value}".encode("utf-8")).hexdigest()[:16]
        return {
            "content_id": content_id,
            "instagram": story,
            "facebook": f"{facebook_context}\n\n{story}",
            "youtube": f"{story}\n\n{youtube_label}{viewer_value}",
        }
