"""Voice-timing preflight run before AION spends work on scene images."""

import math
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

    # Owner, 2026-10-03: instead of cutting an overlong line down, "เพิ่มฉาก
    # เข้าไปให้พอดีคำ" -- give it as many scenes as its measured voice needs.
    # Each resulting scene is aimed at TARGET_PART_SECONDS so it keeps the
    # fast cut a Short depends on and stays well inside the 12-second hold.
    # Every extra scene is a paid image and motion clip, hence the ceiling.
    TARGET_PART_SECONDS = 8.0
    MAX_SPLIT_PARTS = 6

    @classmethod
    def _parts_needed(cls, audio_seconds):
        try:
            seconds = float(audio_seconds) + AudioVisualTimingGate.END_HOLD_SECONDS
        except (TypeError, ValueError):
            return 2
        return max(2, min(cls.MAX_SPLIT_PARTS, math.ceil(seconds / cls.TARGET_PART_SECONDS)))

    @staticmethod
    def _split_narration(narration, parts=2):
        """Split one overlong spoken beat into up to `parts` readable pieces.

        Prefers a sentence or phrase pause nearest each equal-share point and
        only falls back to a word boundary when no pause is close. Never
        truncates words or changes the spoken claim. Returns a list of at
        least two pieces, or None when the line cannot be split sensibly.
        """
        text = " ".join(str(narration or "").split())
        parts = max(2, int(parts))
        pauses = [match.end() for match in re.finditer(r"[.!?…;,:]+(?:[\"')\]]*)\s+", text)]
        words = [match.end() for match in re.finditer(r"\s+(?=[^\s])", text)]
        if not pauses and len(text.split()) < 8:
            return None
        share = len(text) / parts
        cuts = []
        for index in range(1, parts):
            target = share * index
            pause = min(pauses, key=lambda point: abs(point - target), default=None)
            if pause is not None and abs(pause - target) <= share * 0.5:
                cut = pause
            elif words:
                cut = min(words, key=lambda point: abs(point - target))
            else:
                continue
            if cut not in cuts:
                cuts.append(cut)
        cuts.sort()
        pieces, start = [], 0
        for cut in cuts + [len(text)]:
            piece = text[start:cut].strip()
            if piece:
                pieces.append(piece)
            start = cut
        return pieces if len(pieces) >= 2 and all(len(piece.split()) >= 2 for piece in pieces) else None

    @classmethod
    def repair_episode_timing(cls, episode, synthesize=None, duration_reader=None, remaining_passes=2):
        """Boundedly repair narration that exceeds the visual safety window.

        The first measured preflight is authoritative. Each overlong source
        beat is split once into as many adjacent beats as its measured voice
        needs (see _parts_needed), retaining the original narration as
        provenance, then every resulting beat is measured again.
        A bounded second pass can catch a different untouched beat whose live
        voice duration changes between measurements. No image is generated
        during either pass and no episode is discarded.
        """
        first_report = cls.assess_episode(episode, synthesize, duration_reader)
        failures = []
        for item in first_report.get("checks", []):
            scene_index = int(item.get("scene") or 0) - 1
            scene = (episode.get("scenes") or [])[scene_index] if scene_index >= 0 else {}
            if (
                "narration-exceeds-safe-scene-window" in (item.get("reasons") or [])
                and not scene.get("narration_timing_repair")
            ):
                failures.append(item)
        if not failures:
            first_report["timing_repair"] = {"attempted": False, "repaired_scenes": []}
            return first_report

        failed_numbers = {item["scene"] for item in failures}
        repaired_scenes, revised_scenes = [], []
        for scene_number, scene in enumerate(episode.get("scenes") or [], 1):
            if scene_number not in failed_numbers:
                revised_scenes.append(scene)
                continue
            failed_item = next(item for item in failures if item["scene"] == scene_number)
            parts = cls._split_narration(
                scene.get("narration"), cls._parts_needed(failed_item.get("audio_seconds"))
            )
            if not parts:
                revised_scenes.append(scene)
                continue
            original = str(scene.get("narration") or "").strip()
            base_repair = {
                "version": "narration-aware-split-v1",
                "source_scene": scene_number,
                "source_narration": original,
                "parts": len(parts),
            }
            beat = scene.get("beat", "story")
            visual = str(scene.get("visual") or "").strip()
            pieces = []
            for part_number, narration in enumerate(parts, 1):
                piece = dict(scene)
                piece["narration"] = narration
                suffix = "setup" if part_number == 1 else "continuation" if part_number == 2 else f"continuation-{part_number}"
                piece["beat"] = f"{beat}—{suffix}"
                step = "first" if part_number == 1 else "next"
                piece["visual"] = f"{visual} Show the {step} causal step in a distinct composition."
                piece["narration_timing_repair"] = {**base_repair, "part": part_number}
                pieces.append(piece)
            revised_scenes.extend(pieces)
            repaired_scenes.append(scene_number)

        if not repaired_scenes:
            first_report["timing_repair"] = {"attempted": True, "repaired_scenes": []}
            return first_report

        for index, scene in enumerate(revised_scenes, 1):
            scene["n"] = index
        episode["scenes"] = revised_scenes
        episode["target_duration_seconds"] = len(revised_scenes) * int(episode.get("scene_seconds") or 0)
        # The storyboard has a pair of inspectable planning ledgers.  A
        # repaired scene must update both rather than leaving a valid media
        # plan behind stale metadata that blocks Studio later.
        visual_narrative = episode.get("visual_narrative")
        if isinstance(visual_narrative, dict):
            visual_narrative["scene_progression"] = [scene["beat"] for scene in revised_scenes]
        fact_first_visual = episode.get("fact_first_visual")
        if isinstance(fact_first_visual, dict):
            from brain.fact_first_visual_gate import FactFirstVisualGate
            fact_first_visual["scene_roles"] = FactFirstVisualGate.plan(
                episode.get("topic_key") or episode.get("wonder_hook"),
                episode.get("sources"),
                revised_scenes,
            )["scene_roles"]
        episode["narration_timing_repairs"] = {
            "version": "narration-aware-split-v1",
            "source_scene_numbers": repaired_scenes,
            "policy": "one automatic split per originally overlong scene, into as many scenes as its measured voice needs; all resulting scenes are remeasured",
        }
        repaired_report = cls.assess_episode(episode, synthesize, duration_reader)
        repaired_report["timing_repair"] = {
            "attempted": True,
            "repaired_scenes": repaired_scenes,
            "remeasured": True,
        }
        if not repaired_report.get("eligible") and remaining_passes > 1:
            # Voice delivery is measured live and can vary slightly. A second
            # bounded pass may repair another *untouched* source beat, but
            # never subdivides a scene that was already repaired above.
            follow_up = cls.repair_episode_timing(
                episode, synthesize, duration_reader, remaining_passes=remaining_passes - 1
            )
            follow_up["timing_repair"]["initial_repaired_scenes"] = repaired_scenes
            return follow_up
        return repaired_report
