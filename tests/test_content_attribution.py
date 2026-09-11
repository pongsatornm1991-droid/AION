import json
import tempfile
import unittest

from brain.content_attribution import ContentAttributionEngine
from brain.memory import MemoryEngine


class ContentAttributionTests(unittest.TestCase):
    def test_links_instagram_metrics_to_the_matching_content_id(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            reel = memory.remember("published_reels", json.dumps({
                "caption": "AION follows a question across a changing landscape.",
                "ig_caption": "AION follows a question across a changing landscape. #AI",
                "platform_captions": {"content_id": "story-123", "instagram": "AION follows a question across a changing landscape."},
            }), memory_type="action", source="test", importance=3)
            memory.remember("social_feedback", json.dumps({
                "kind": "media", "media_id": "ig-1", "caption": "AION follows a question across a changing landscape. #AI",
                "like_count": 5, "comments_count": 2,
            }), memory_type="observation", source="instagram-feedback", importance=2)
            report = ContentAttributionEngine(memory).capture_instagram_once()
            self.assertEqual(1, report["recorded"])
            saved = json.loads(memory.all("content_attribution")[0]["content"])
            self.assertEqual("story-123", saved["content_id"])
            self.assertEqual(reel["id"], saved["reel_memory_id"])

    def test_does_not_guess_a_match_for_legacy_content(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember("published_reels", json.dumps({"caption": "An old caption"}), memory_type="action", source="test", importance=1)
            memory.remember("social_feedback", json.dumps({"kind": "media", "media_id": "ig-1", "caption": "An old caption"}), memory_type="observation", source="instagram-feedback", importance=2)
            self.assertEqual(0, ContentAttributionEngine(memory).capture_instagram_once()["recorded"])
