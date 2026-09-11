import tempfile
import unittest
from pathlib import Path

from brain.memory import MemoryEngine
from brain.youtube_creator_queue import YouTubeCreatorQueue


class YouTubeCreatorQueueTests(unittest.TestCase):
    def _episode(self, root):
        series = Path(root) / "content" / "creator_series"
        images = Path(root) / "assets" / "images"
        reels = Path(root) / "content" / "reels"
        series.mkdir(parents=True)
        images.mkdir(parents=True)
        reels.mkdir(parents=True)
        for number in range(3):
            (images / f"{number}.png").write_bytes(b"image")
        (series / "episode.json").write_text(__import__("json").dumps({
            "id": "episode", "series": "AION Wonders", "title": "A useful question",
            "status": "production-ready-assets-and-script", "format": "illustrated-narrated-short",
            "target_duration_seconds": 18, "scene_seconds": 6,
            "audience_promise": "Viewers learn how a careful question can make a mystery easier to explore.",
            "wonder_hook": "Could a small question change how we see the world?", "creative_device": "journey",
            "age_layers": {"children": "Ask why.", "family": "Talk together.", "deeper": "Test a claim."},
            "science_boundary": "This is a story prompt, not scientific proof.",
            "sources": [{"url": "https://example.test/one"}, {"url": "https://example.test/two"}],
            "scenes": [
                {"n": n, "image": f"assets/images/{n}.png", "visual": "AION explores a new place.", "narration": "AION asks a careful question."}
                for n in range(3)
            ],
        }), encoding="utf-8")

    def test_prepares_rendered_episode_without_uploading(self):
        with tempfile.TemporaryDirectory() as root:
            self._episode(root)
            (Path(root) / "content" / "reels" / "episode.mp4").write_bytes(b"video")
            memory = MemoryEngine(Path(root) / "memory")
            queue = YouTubeCreatorQueue(memory, root)
            self.assertEqual("upload-ready", queue.candidates()[0]["status"])
            report = queue.prepare_once()
            self.assertEqual("prepared-for-review", report["stage"])
            self.assertEqual("awaiting-human-confirmation", report["upload_status"])
            self.assertEqual("already-prepared", queue.candidates()[0]["status"])
            self.assertEqual("no-upload-ready-creator-episode", queue.prepare_once()["stage"])
