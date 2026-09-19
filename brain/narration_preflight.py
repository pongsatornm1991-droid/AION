"""Voice-timing preflight run before AION spends work on scene images."""

import shutil
import tempfile

from brain.audio_visual_timing import AudioVisualTimingGate


class NarrationPreflight:
    """Measure the actual selected voice against each storyboard beat."""

    @staticmethod
    def _ffmpeg():
        path = shutil.which("ffmpeg")
        if path:
            return path
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            return None

    @classmethod
    def assess_episode(cls, episode, synthesize=None, duration_reader=None):
        """Return a no-guesswork timing decision for one storyboard.

        This uses the same voice provider and timing tolerance as the final
        renderer. It only writes temporary audio, so it never creates media,
        alters accounts, or contacts a publishing platform.
        """
        from tools.voice import synthesize_reel_voice
        from tools.reel_render import _audio_duration

        synthesize = synthesize or synthesize_reel_voice
        ffmpeg = cls._ffmpeg()
        if not ffmpeg and duration_reader is None:
            return {
                "eligible": False,
                "state": "blocked",
                "reasons": ["narration-preflight-missing-ffmpeg"],
                "detail": "ตรวจความยาวเสียงจริงไม่ได้ จึงยังห้ามเริ่มผลิตภาพ",
            }
        duration_reader = duration_reader or (lambda audio: _audio_duration(ffmpeg, audio))
        scene_seconds = int(episode.get("scene_seconds") or 0)
        scenes = episode.get("scenes") or []
        checks = []
        with tempfile.TemporaryDirectory(prefix="aion-narration-preflight-") as directory:
            for index, scene in enumerate(scenes, 1):
                audio = f"{directory}/scene-{index:02d}.mp3"
                narration = str(scene.get("narration") or "").strip()
                if not narration or not synthesize(narration, audio):
                    checks.append({"scene": index, "eligible": False, "reason": "voice-synthesis-failed"})
                    continue
                timing = AudioVisualTimingGate.assess(
                    duration_reader(audio), scene_seconds, max_trailing_silence=2.0
                )
                checks.append({"scene": index, **timing})
        failures = [item for item in checks if not item.get("eligible")]
        return {
            "eligible": not failures,
            "state": "pass" if not failures else "return-to-story",
            "episode_id": episode.get("id"),
            "checks": checks,
            "reasons": [f"scene-{item['scene']}:{','.join(item.get('reasons') or [item.get('reason', 'timing-failed')])}" for item in failures],
            "detail": "เสียงทุกฉากพอดีกับภาพ 5 วินาที ก่อนเริ่มผลิตภาพ" if not failures else "มีบทที่ยาวหรือสั้นเกินจังหวะภาพ ส่งกลับฝ่ายเรื่องเล่าก่อนสร้างภาพ",
        }
