"""Offline tests for posting Thai-audio versions of published Shorts to Facebook."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain.memory import MemoryEngine
from brain.thai_dub_cycle import SCRIPT_VERSION
from brain.thai_facebook_crosspost import MAX_ATTEMPTS, ThaiFacebookCrosspost, mux_thai_audio


class MuxTests(unittest.TestCase):
    def run_mux(self, video_seconds, audio_seconds):
        commands = []
        durations = {"v.mp4": video_seconds, "a.mp3": audio_seconds}
        info = mux_thai_audio(
            "v.mp4", "a.mp3", "out.mp4", ffmpeg="ffmpeg",
            duration_reader=lambda path: durations[path], runner=commands.append,
        )
        return info, commands[0]

    def test_shorter_thai_audio_is_padded_and_the_video_is_copied_untouched(self):
        info, command = self.run_mux(94.37, 93.74)
        self.assertFalse(info["reencoded"])
        self.assertEqual("copy", command[command.index("-c:v") + 1])
        self.assertIn("apad=whole_dur=94.370", command[command.index("-af") + 1])
        self.assertEqual("94.370", command[command.index("-t") + 1])
        self.assertEqual("0:v:0", command[command.index("-map") + 1])
        self.assertEqual("1:a:0", command[command.index("-map", command.index("-map") + 1) + 1])

    def test_longer_thai_audio_holds_the_last_frame_instead_of_cutting_speech(self):
        info, command = self.run_mux(90.0, 98.0)
        self.assertTrue(info["reencoded"])
        self.assertIn("tpad=stop_mode=clone", command[command.index("-vf") + 1])
        self.assertEqual("libx264", command[command.index("-c:v") + 1])
        self.assertGreaterEqual(float(command[command.index("-t") + 1]), 98.0)

    def test_an_unreadable_duration_is_an_error_not_a_guess(self):
        with self.assertRaises(RuntimeError):
            mux_thai_audio("v.mp4", "a.mp3", "o.mp4", ffmpeg="ffmpeg",
                           duration_reader=lambda path: None, runner=lambda cmd: None)


class ThaiFacebookCrosspostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.memory = MemoryEngine(root=str(self.tmp / "memory"))
        (self.tmp / "content" / "reels").mkdir(parents=True)
        (self.tmp / "content" / "reels_thai").mkdir(parents=True)
        self.quality = mock.patch(
            "brain.thai_facebook_crosspost.VideoQualityGate.assess", return_value={"eligible": True})
        self.quality.start()
        self.addCleanup(self.quality.stop)

    def dub(self, episode_id, generated_at, with_files=True, script_version=SCRIPT_VERSION):
        if with_files:
            (self.tmp / "content" / "reels" / f"{episode_id}.mp4").write_bytes(b"v")
            (self.tmp / "content" / "reels_thai" / f"{episode_id}.mp3").write_bytes(b"a")
        record = {
            "episode_id": episode_id, "video_id": f"yt-{episode_id}", "title_th": f"ชื่อ {episode_id}",
            "description_th": "ย่อหน้าทั่วไป\n\nจงระบุให้ชัดว่ายังไม่ยืนยันอะไร\n\n#Tag1 #Shorts", "audio_path": f"content/reels_thai/{episode_id}.mp3",
            "generated_at": generated_at, "script_version": script_version,
        }
        self.memory.remember("youtube_thai_dubs", json.dumps(record, ensure_ascii=False),
                             memory_type="action", source=f"aion-thai-dub:{episode_id}", importance=3)

    def cycle(self):
        return ThaiFacebookCrosspost(self.memory, self.tmp)

    @staticmethod
    def fake_mux(video, audio, output):
        Path(output).write_bytes(b"thai-video")
        return {"output_seconds": 94.0}

    def test_posts_the_newest_dub_first_with_a_thai_caption_and_a_youtube_link(self):
        self.dub("old", "2026-09-26T00:00:00")
        self.dub("new", "2026-10-02T00:00:00")
        posted = []

        def publisher(path, caption=""):
            posted.append((Path(path).read_bytes(), caption))
            return {"id": "fb-1"}

        report = self.cycle().publish_once(facebook_publisher=publisher, muxer=self.fake_mux)
        self.assertEqual("published", report["stage"])
        self.assertEqual("new", report["episode_id"])
        self.assertEqual(b"thai-video", posted[0][0])
        self.assertIn("ชื่อ new", posted[0][1])
        self.assertIn("https://www.youtube.com/shorts/yt-new", posted[0][1])
        self.assertIn("ฉันคือ AI", posted[0][1])
        self.assertIn("#Tag1 #Shorts", posted[0][1])
        # The generic description paragraphs are not carried over to Facebook.
        self.assertNotIn("จงระบุให้ชัดว่า", posted[0][1])

    def test_a_dub_from_an_older_script_is_never_posted_until_it_has_been_redone(self):
        # 2026-10-04: the first dubs were word-for-word translations; the owner
        # wanted them redone as storytelling BEFORE anything reached Facebook.
        self.dub("translated", "2026-10-02T00:00:00", script_version=None)
        publisher = mock.Mock()
        report = self.cycle().publish_once(facebook_publisher=publisher, muxer=self.fake_mux)
        self.assertEqual("nothing-to-publish", report["stage"])
        publisher.assert_not_called()
        # Once the episode has been dubbed again, the newer record is the one posted.
        self.dub("translated", "2026-10-05T00:00:00")
        report = self.cycle().publish_once(facebook_publisher=lambda path, caption="": {"id": "x"}, muxer=self.fake_mux)
        self.assertEqual("translated", report["episode_id"])

    def test_each_episode_is_posted_at_most_once(self):
        self.dub("only", "2026-10-02T00:00:00")
        calls = []
        publisher = lambda path, caption="": calls.append(path) or {"id": "x"}
        self.cycle().publish_once(facebook_publisher=publisher, muxer=self.fake_mux)
        second = self.cycle().publish_once(facebook_publisher=publisher, muxer=self.fake_mux)
        self.assertEqual("nothing-to-publish", second["stage"])
        self.assertEqual(1, len(calls))

    def test_a_failed_post_is_retried_a_bounded_number_of_times_then_left_alone(self):
        self.dub("flaky", "2026-10-02T00:00:00")

        def broken(path, caption=""):
            raise RuntimeError("(#200) permission denied")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            report = self.cycle().publish_once(facebook_publisher=broken, muxer=self.fake_mux)
            self.assertEqual("failed", report["stage"])
            self.assertEqual(attempt, report["attempts"])
            self.assertIn("permission denied", report["error"])
        self.assertEqual("nothing-to-publish", self.cycle().publish_once(facebook_publisher=broken, muxer=self.fake_mux)["stage"])

    def test_an_episode_missing_its_video_or_audio_is_skipped_for_the_next_one(self):
        self.dub("ready", "2026-09-26T00:00:00")
        self.dub("missing-files", "2026-10-02T00:00:00", with_files=False)
        report = self.cycle().publish_once(
            facebook_publisher=lambda path, caption="": {"id": "x"}, muxer=self.fake_mux)
        self.assertEqual("ready", report["episode_id"])

    def test_a_video_that_fails_the_quality_gate_is_never_posted(self):
        self.dub("bad", "2026-10-02T00:00:00")
        publisher = mock.Mock()
        with mock.patch("brain.thai_facebook_crosspost.VideoQualityGate.assess", return_value={"eligible": False}):
            report = self.cycle().publish_once(facebook_publisher=publisher, muxer=self.fake_mux)
        self.assertEqual("nothing-to-publish", report["stage"])
        publisher.assert_not_called()

    def test_dry_run_reports_without_rendering_or_posting(self):
        self.dub("one", "2026-10-02T00:00:00")
        publisher, muxer = mock.Mock(), mock.Mock()
        report = self.cycle().publish_once(facebook_publisher=publisher, muxer=muxer, dry_run=True)
        self.assertEqual("would-publish", report["stage"])
        publisher.assert_not_called()
        muxer.assert_not_called()
        self.assertEqual(0, len(self.memory.all("thai_facebook_crossposts")))

    def test_batch_stops_at_the_first_non_success_and_respects_the_limit(self):
        for index in range(3):
            self.dub(f"e{index}", f"2026-10-0{index + 1}T00:00:00")
        publisher = lambda path, caption="": {"id": "x"}
        report = self.cycle().publish_batch(limit=2, facebook_publisher=publisher, muxer=self.fake_mux)
        self.assertEqual(2, len(report["results"]))
        self.assertEqual(1, len(self.cycle().candidates()))


if __name__ == "__main__":
    unittest.main()
