import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain.memory import MemoryEngine
from brain.thai_dub_cycle import CATEGORY, SCRIPT_VERSION, ThaiDubCycle, has_unsafe_claim
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


class FilenameSlugTests(unittest.TestCase):
    def test_builds_a_readable_slug_from_the_real_video_title(self):
        # Owner, 2026-09-27: "อยากให้ตั้งชื่อตามคลิป จะได้หาเจอ" -- the old
        # filename was the opaque episode id (e.g.
        # "aion-auto-0b5a0385b87d-7d3a5028-short-thai.mp3"), unrecognizable
        # at a glance in content/reels_thai/.
        slug = ThaiDubCycle._filename_slug("AION Wonders: Why do fireflies glow in the dark? #Fireflies")
        self.assertEqual("fireflies-glow-dark", slug)

    def test_drops_the_channel_name_noise_words_but_keeps_real_content(self):
        slug = ThaiDubCycle._filename_slug("AION Explains: Why do fireflies glow in the dark?")
        self.assertNotIn("aion", slug)
        self.assertNotIn("explains", slug)
        self.assertIn("fireflies", slug)

    def test_falls_back_to_a_placeholder_when_no_keyword_survives_at_all(self):
        self.assertEqual("episode", ThaiDubCycle._filename_slug("How is it"))


class ThaiDubCycleTests(unittest.TestCase):
    def test_a_relative_root_is_resolved_to_an_absolute_path(self):
        # Regression: a relative root (e.g. ".") used to be kept as-is, so
        # the final audio file's output path, built as self.root / "...",
        # stayed relative too -- and _synthesize_track() runs ffmpeg's
        # concat step with cwd set to a temp directory, so ffmpeg resolved
        # that relative output path against the temp dir instead of the
        # real project tree and failed with "No such file or directory"
        # on a path that looked correct at a glance. Confirmed in a real
        # production run, 2026-09-27.
        import os
        cwd = os.getcwd()
        cycle = _cycle(MemoryEngine(tempfile.mkdtemp()), ".", SAFE_TRANSLATION)
        self.assertTrue(cycle.root.is_absolute())
        self.assertEqual(Path(cwd), cycle.root)

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
            self.assertEqual("content/reels_thai/live-title-vid-1-thai.mp3", result["audio_path"])
            localize_fn.assert_called_once_with("vid-1", "th", "ทำไมแผนที่ถึงแตกต่างกัน", "คำอธิบายภาษาไทย")
            saved = json.loads(memory.all(CATEGORY)[0]["content"])
            self.assertEqual("ep-1", saved["episode_id"])

    def test_prefers_the_newest_published_episode_over_the_oldest(self):
        # Regression, found running this for real on 2026-09-27: 12
        # already-published episodes had no dub yet (this feature
        # launched after they did), so an oldest-first order meant a
        # brand new release -- the one actually asked about, the same
        # night it published -- would queue behind that whole backlog.
        import time
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-old")
            _write_episode(root, "ep-new")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-old", "vid-old")
            time.sleep(1.1)
            _publish_record(memory, "ep-new", "vid-new")
            localize_fn = mock.Mock()
            with mock.patch("brain.thai_dub_cycle.subprocess.run"), \
                 mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=5.0):
                cycle = _cycle(memory, root, SAFE_TRANSLATION, localize_fn=localize_fn)
                result = cycle.dub_once()
            self.assertEqual("ep-new", result["episode_id"])

    def test_dub_batch_dubs_up_to_the_limit_newest_first(self):
        import time
        with tempfile.TemporaryDirectory() as root:
            for episode_id in ("ep-1", "ep-2", "ep-3"):
                _write_episode(root, episode_id)
            memory = MemoryEngine(Path(root) / "memory")
            for episode_id in ("ep-1", "ep-2", "ep-3"):
                _publish_record(memory, episode_id, f"vid-{episode_id}")
                time.sleep(1.1)
            with mock.patch("brain.thai_dub_cycle.subprocess.run"), \
                 mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=5.0):
                cycle = _cycle(memory, root, SAFE_TRANSLATION, localize_fn=mock.Mock())
                report = cycle.dub_batch(limit=2)
            self.assertEqual("dub-batch-complete", report["stage"])
            self.assertEqual(2, report["dubbed_count"])
            self.assertEqual(["ep-3", "ep-2"], [item["episode_id"] for item in report["results"]])

    def test_dub_batch_stops_early_on_the_first_failure(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            _write_episode(root, "ep-2")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            _publish_record(memory, "ep-2", "vid-2")
            cycle = _cycle(memory, root, SAFE_TRANSLATION, tts_fn=lambda text, path: False)
            report = cycle.dub_batch(limit=3)
            self.assertEqual(0, report["dubbed_count"])
            self.assertEqual(1, len(report["results"]))

    def test_skips_an_episode_that_was_already_dubbed(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            memory.remember(CATEGORY, json.dumps({"episode_id": "ep-1", "script_version": SCRIPT_VERSION}),
                            memory_type="action", source="aion-thai-dub:ep-1")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual({"stage": "nothing-to-dub"}, cycle.dub_once())

    def test_a_dub_made_with_an_older_script_is_redone_but_a_skip_marker_never_is(self):
        # 2026-10-04: the first dubs were word-for-word translations; they are
        # dubbed again with the storytelling script. Backlog-skip markers carry
        # no audio and stay skipped.
        with tempfile.TemporaryDirectory() as root:
            for episode_id in ("old", "skipped"):
                _write_episode(root, episode_id)
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "old", "vid-old")
            _publish_record(memory, "skipped", "vid-skipped")
            memory.remember(CATEGORY, json.dumps({"episode_id": "old", "audio_path": "x.mp3"}),
                            memory_type="action", source="aion-thai-dub:old")
            memory.remember(CATEGORY, json.dumps({"episode_id": "skipped", "skipped": True}),
                            memory_type="action", source="aion-thai-dub:skipped")
            cycle = _cycle(memory, root, SAFE_TRANSLATION)
            self.assertEqual(["old"], [episode for _, episode, _ in cycle._published_candidates()])

    def test_a_new_dub_record_is_stamped_with_the_script_version(self):
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            with mock.patch("brain.thai_dub_cycle.subprocess.run"),                  mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=5.0):
                _cycle(memory, root, SAFE_TRANSLATION).dub_once()
            self.assertEqual(SCRIPT_VERSION, json.loads(memory.all(CATEGORY)[0]["content"])["script_version"])

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

    def test_a_translation_missing_title_or_description_is_reported_not_a_crash(self):
        # Regression: a translation JSON with the right narration count but
        # no "title"/"description" keys used to raise an uncaught KeyError
        # in dub_once() (those keys were read outside any try/except),
        # crashing the whole run instead of returning a clean stage.
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            incomplete_translation = json.dumps({"narration": ["บรรทัดหนึ่ง", "บรรทัดสอง"]})
            localize_fn = mock.Mock()
            cycle = _cycle(memory, root, incomplete_translation, localize_fn=localize_fn)
            result = cycle.dub_once()
            self.assertEqual("translation-failed", result["stage"])
            localize_fn.assert_not_called()

    def test_a_zero_length_synthesized_clip_fails_cleanly_instead_of_hanging(self):
        # Regression: _atempo_chain(0.0) looped forever (0.0 / 0.5 stays
        # 0.0), reachable whenever a scene's synthesized clip comes back
        # with zero measurable duration.
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            localize_fn = mock.Mock()
            with mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=0.0):
                cycle = _cycle(memory, root, SAFE_TRANSLATION, localize_fn=localize_fn)
                result = cycle.dub_once()
            self.assertEqual("audio-synthesis-failed", result["stage"])
            self.assertTrue(result["localization_written"])

    def test_atempo_chain_never_hangs_on_a_non_positive_factor(self):
        self.assertEqual("atempo=1.0000", ThaiDubCycle._atempo_chain(0.0))
        self.assertEqual("atempo=1.0000", ThaiDubCycle._atempo_chain(-2.0))

    def test_clip_duration_suppresses_the_console_window_on_windows(self):
        import brain.thai_dub_cycle as thai_dub_cycle_module
        cycle = _cycle(MemoryEngine(tempfile.mkdtemp()), ".", SAFE_TRANSLATION)
        with mock.patch("brain.thai_dub_cycle.subprocess.run") as run:
            run.return_value = mock.Mock(stderr="Duration: 00:00:05.00, start: 0.000000")
            cycle._clip_duration("some.mp3")
        run.assert_called_once()
        self.assertEqual(thai_dub_cycle_module._NO_WINDOW, run.call_args.kwargs.get("creationflags"))

    def test_ffmpeg_subprocess_calls_suppress_the_console_window_on_windows(self):
        import brain.thai_dub_cycle as thai_dub_cycle_module
        with tempfile.TemporaryDirectory() as root:
            _write_episode(root, "ep-1")
            memory = MemoryEngine(Path(root) / "memory")
            _publish_record(memory, "ep-1", "vid-1")
            with mock.patch("brain.thai_dub_cycle.subprocess.run") as run, \
                 mock.patch.object(ThaiDubCycle, "_clip_duration", return_value=5.0):
                run.return_value = mock.Mock(returncode=0)
                cycle = _cycle(memory, root, SAFE_TRANSLATION)
                cycle.dub_once()
            self.assertTrue(run.call_args_list, "expected at least one subprocess.run call")
            for call in run.call_args_list:
                self.assertEqual(thai_dub_cycle_module._NO_WINDOW, call.kwargs.get("creationflags"))


if __name__ == "__main__":
    unittest.main()


class SequenceProvider:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.responses[min(len(self.prompts), len(self.responses)) - 1]


def _translation(*lines):
    return json.dumps({"title": "ชื่อ", "description": "คำอธิบาย", "narration": list(lines)}, ensure_ascii=False)


class StorytellingTranslationTests(unittest.TestCase):
    # Owner, 2026-10-04: the Thai audio should be told as content (storytelling),
    # not the English narration translated word for word, and each line sized to
    # its scene so the voice is not rushed or dragged by the time-fit.
    def cycle(self, provider):
        return ThaiDubCycle(memory=None, root=".", provider=provider, ffmpeg_path="x", tts_fn=lambda t, p: True,
                            snippet_fn=lambda v: {}, localize_fn=lambda *a: None)

    def test_the_prompt_asks_for_spoken_storytelling_and_gives_each_line_its_size(self):
        provider = SequenceProvider(_translation("หนึ่ง", "สอง"))
        self.cycle(provider)._translate("T", "D", ["Line one.", "Line two."], [5.0, 8.0])
        prompt = provider.prompts[0]
        self.assertIn("SPOKEN STORYTELLING", prompt)
        self.assertIn("It is NOT a translation", prompt)
        self.assertIn('"max_chars": 65', prompt)
        self.assertIn('"max_chars": 104', prompt)
        self.assertIn("แหล่งข้อมูล", prompt)  # named as wording to avoid

    def test_a_line_far_too_long_for_its_scene_is_retried_once_with_a_shorten_note(self):
        long_line = "ก" * 200
        provider = SequenceProvider(_translation("สั้น", long_line), _translation("สั้น", "พอดี"))
        data = self.cycle(provider)._translate("T", "D", ["a", "b"], [5.0, 5.0])
        self.assertEqual(["สั้น", "พอดี"], data["narration"])
        self.assertEqual(2, len(provider.prompts))
        self.assertIn("line(s) 2", provider.prompts[1])

    def test_a_line_that_stays_too_long_is_reported_never_silently_rushed(self):
        long_line = "ก" * 200
        provider = SequenceProvider(_translation("สั้น", long_line))
        with self.assertRaises(ValueError) as caught:
            self.cycle(provider)._translate("T", "D", ["a", "b"], [5.0, 5.0])
        self.assertIn("line(s) 2", str(caught.exception))
        self.assertEqual(2, len(provider.prompts))

    def test_without_scene_durations_the_old_behaviour_is_unchanged(self):
        provider = SequenceProvider(_translation("หนึ่ง", "สอง"))
        data = self.cycle(provider)._translate("T", "D", ["Line one.", "Line two."])
        self.assertEqual(["หนึ่ง", "สอง"], data["narration"])
        self.assertEqual(1, len(provider.prompts))
        self.assertNotIn("max_chars", provider.prompts[0].split("NARRATION (in order):")[1])

