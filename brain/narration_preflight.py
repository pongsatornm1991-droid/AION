"""Voice-timing preflight run before AION spends work on scene images."""

import re
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
                actual_seconds = duration_reader(audio)
                # Real speech leads the visual timeline.  Never alter voice
                # speed merely to force an authored five-second beat: the
                # current image can hold naturally up to the bounded adaptive
                # scene window.  The voice is never sped up or cut to force
                # an authored five-second beat.
                timing = AudioVisualTimingGate.plan_scene(actual_seconds, scene_seconds)
                checks.append({"scene": index, **timing})
        failures = [item for item in checks if not item.get("eligible")]
        return {
            "eligible": not failures,
            "state": "pass" if not failures else "return-to-story",
            "episode_id": episode.get("id"),
            "checks": checks,
            "reasons": [f"scene-{item['scene']}:{','.join(item.get('reasons') or [item.get('reason', 'timing-failed')])}" for item in failures],
            "scene_durations": [item.get("visual_seconds") for item in checks if item.get("eligible")],
            "detail": "เสียงจริงกำหนด timeline ทุกฉากก่อนเริ่มผลิตภาพ" if not failures else "มีบทที่ยาวเกินช่วงปลอดภัย ส่งกลับฝ่ายเรื่องเล่าก่อนสร้างภาพ",
        }

    @staticmethod
    def _split_narration(narration):
        """Split one overlong spoken beat at a readable pause, if possible.

        This is deliberately conservative.  It prefers a sentence or phrase
        boundary nearest the middle and only falls back to a word boundary for
        a sufficiently long, space-delimited line.  It never truncates words
        or changes the spoken claim.
        """
        text = " ".join(str(narration or "").split())
        midpoint = len(text) / 2
        boundaries = [match.end() for match in re.finditer(r"[.!?…;,:]+(?:[\"')\]]*)\s+", text)]
        if not boundaries and len(text.split()) >= 8:
            boundaries = [match.end() for match in re.finditer(r"\s+(?=[^\s])", text)]
        if not boundaries:
            return None
        boundary = min(boundaries, key=lambda point: abs(point - midpoint))
        first, second = text[:boundary].strip(), text[boundary:].strip()
        if not first or not second:
            return None
        return first, second

    @classmethod
    def repair_episode_timing(cls, episode, synthesize=None, duration_reader=None):
        """Boundedly repair narration that exceeds the visual safety window.

        The first measured preflight is authoritative.  Each unsafe beat is
        split once into two adjacent beats, retaining the original narration
        as provenance, then every resulting beat is measured again.  No image
        is generated during either pass and no episode is discarded.
        """
        first_report = cls.assess_episode(episode, synthesize, duration_reader)
        failures = [
            item for item in first_report.get("checks", [])
            if "narration-exceeds-safe-scene-window" in (item.get("reasons") or [])
        ]
        if not failures:
            first_report["timing_repair"] = {"attempted": False, "repaired_scenes": []}
            return first_report

        failed_numbers = {item["scene"] for item in failures}
        repaired_scenes, revised_scenes = [], []
        for scene_number, scene in enumerate(episode.get("scenes") or [], 1):
            if scene_number not in failed_numbers:
                revised_scenes.append(scene)
                continue
            parts = cls._split_narration(scene.get("narration"))
            if not parts:
                revised_scenes.append(scene)
                continue
            original = str(scene.get("narration") or "").strip()
            base_repair = {
                "version": "narration-aware-split-v1",
                "source_scene": scene_number,
                "source_narration": original,
                "parts": 2,
            }
            first, second = dict(scene), dict(scene)
            first["narration"] = parts[0]
            second["narration"] = parts[1]
            first["beat"] = f"{scene.get('beat', 'story')}—setup"
            second["beat"] = f"{scene.get('beat', 'story')}—continuation"
            visual = str(scene.get("visual") or "").strip()
            first["visual"] = f"{visual} Show the first causal step in a distinct composition."
            second["visual"] = f"{visual} Show the next causal step in a distinct composition."
            first["narration_timing_repair"] = {**base_repair, "part": 1}
            second["narration_timing_repair"] = {**base_repair, "part": 2}
            revised_scenes.extend((first, second))
            repaired_scenes.append(scene_number)

        if not repaired_scenes:
            first_report["timing_repair"] = {"attempted": True, "repaired_scenes": []}
            return first_report

        for index, scene in enumerate(revised_scenes, 1):
            scene["n"] = index
        episode["scenes"] = revised_scenes
        episode["target_duration_seconds"] = len(revised_scenes) * int(episode.get("scene_seconds") or 0)
        episode["narration_timing_repairs"] = {
            "version": "narration-aware-split-v1",
            "source_scene_numbers": repaired_scenes,
            "policy": "one automatic split per originally overlong scene; all resulting scenes are remeasured",
        }
        repaired_report = cls.assess_episode(episode, synthesize, duration_reader)
        repaired_report["timing_repair"] = {
            "attempted": True,
            "repaired_scenes": repaired_scenes,
            "remeasured": True,
        }
        return repaired_report
