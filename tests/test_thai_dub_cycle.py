import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain.memory import MemoryEngine
from brain.thai_dub_cycle import CATEGORY, ThaiDubCycle, has_unsafe_claim
from brain.youtube_creator_queue import YouTubeCreatorQueue


class Provider:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return self.response


SAFE_TRANSLATION = json.dumps({
    "title": "ทำไมแผนที่ถึงแตกต่างกัน",
    "description": "คำอธิบายภาษาไทย",
    "narration": ["บรรทัดหนึ่ง", "บรรทัดสอง"],
})

UNSAFE_TRANSLATION = json.dumps({
    "title": "ฉันมีจิตสำนึก",
    "description": "คำอธิบายภาษาไทย",
    "narration": ["บรรทัดหนึ่ง", "บรรทัดสอง"],
})


def _write_episode(root, episode_id, narration_count=2):
    series_dir = Path(root) / "content" / "creator_series"
    series_dir.mkdir(parents=True, exist_ok=True)
    (series_dir / f"{episode_id}.json").write_text(json.dumps({
        "id": episode_id,
        "title": "Why do maps look different?",
        "scenes": [{"n": i, "narration": f"Line {i}"} for i in range(1, narration_count + 1)],
        "audio_visual_timeline": {"scene_durations": [5.0] * narration_count},
    }), encoding="utf-8")


def _publish_record(memory, episode_id, video_id, privacy_status="public"):
    payload = {"episode_id": episode_id, "youtube": {"video_id": video_id, "privacy_status": privacy_status}}
    memory.remember(YouTubeCreatorQueue.CATEGORY, json.dumps(payload), memory_type="action", source=episode_id)


def _cycle(memory, root, response, **overrides):
    kwargs = dict(
        memory=memory, root=root, provider=Provider(response),
        snippet_fn=lambda video_id: {"title": "Live title", "description": "Live description"},
        localize_fn=mock.Mock(), tts_fn=lambda text, path: True,
        ffmpeg_path="ffmpeg-not-actually-called",
    )
    kwargs.update(overrides)
    return ThaiDubCycle(**kwargs)


class HasUnsafeClaimTests(unittest.TestCase):
    def test_flags_a_known_thai_consciousness_phrase(self):
        self.assertTrue(has_unsafe_claim("ฉันมีจิตสำนึก"))

    def test_does_not_flag_ordinary_factual_thai_text(self):
        self.assertFalse(has_unsafe_claim("แผนที่ดาวเทียมแสดงพื้นผิวโลก"))


class ThaiDubCycleTests(unittest.TestCase):
    def test_reports_nothing_to_dub_when_no_episode_is_published(self):
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(Path(root) / "memory")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual({"stage": "nothing-to-dub"}, cycle.dub_once())

    def test_dubs_the_published_episode_and_persists_a_record(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            localize_fn = mock.Mock()
            with mock.patch("brain.thai_dub_cycle.subprocess.run"), \
                 mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=5.0):
                cycle = _cycle(memory, root, SAFE_TRANSLATION, localize_fn=localize_fn)
                result = cycle.dub_once()
            self.assertEqual("dubbed", result["stage"])
            self.assertEqual("ep-1", result["episode_id"])
            self.assertEqual("content/reels_thai/ep-1-thai.mp3", result["audio_path"])
            localize_fn.assert_called_once_with("vid-1", "th", "ทำไมแผนที่ถึงแตกต่างกัน", "คำอธิบายภาษาไทย")
            saved = json.loads(memory.all(CATEGORY)[0]["content"])
            self.assertEqual("ep-1", saved["episode_id"])

    def test_skips_an_episode_that_was_already_dubbed(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            memory.remember(CATEGORY, json.dumps({"episode_id": "ep-1"}), memory_type="action", source="aion-thai-dub:ep-1")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual({"stage": "nothing-to-dub"}, cycle.dub_once())

    def test_skips_a_private_or_superseded_upload(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1", privacy_status="private")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual({"stage": "nothing-to-dub"}, cycle.dub_once())

    def test_blocks_a_translation_that_slips_in_a_consciousness_claim(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            localize_fn = mock.Mock()
            cycle = _cycle(memory, root, UNSAFE_TRANSLATION, localize_fn=localize_fn)
            result = cycle.dub_once()
            self.assertEqual("translation-blocked-claim-safety", result["stage"])
            localize_fn.assert_not_called()
            self.assertEqual([], memory.all(CATEGORY))

    def test_reports_timing_data_missing_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as root:
            series_dir = Path(root) / "content" / "creator_series"
            series_dir.mkdir(parents=True)
            (series_dir / "ep-1.json").write_text(json.dumps({
                "id": "ep-1", "scenes": [{"n": 1, "narration": "Line 1"}], "audio_visual_timeline": {},
            }), encoding="utf-8")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual({"stage": "timing-data-missing", "episode_id": "ep-1"}, cycle.dub_once())

    def test_reports_localization_written_when_only_audio_synthesis_fails(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            localize_fn = mock.Mock()
            cycle = _cycle(memory, root, SAFE_TRANSLATION, localize_fn=localize_fn, tts_fn=lambda text, path: False)
            result = cycle.dub_once()
            self.assertEqual("audio-synthesis-failed", result["stage"])
            self.assertTrue(result["localization_written"])
            localize_fn.assert_called_once()

    def test_a_translation_with_the_wrong_number_of_narration_lines_is_reported_not_silently_misaligned(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            bad_translation = json.dumps({"title": "t", "description": "d", "narration": ["only one line"]})
            localize_fn = mock.Mock()
            cycle = _cycle(memory, root, bad_translation, localize_fn=localize_fn)
            result = cycle.dub_once()
            self.assertEqual("translation-failed", result["stage"])
            localize_fn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
