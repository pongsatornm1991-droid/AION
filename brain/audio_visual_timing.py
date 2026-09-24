"""Pre-assembly timing gate for AION Studio narration and visuals.

The final MP4 can conceal a failure when a muxer trims an overlong narration.
This small, deterministic gate inspects the source narration against the
storyboard before final assembly, so Story and Visual receive a usable repair
brief rather than a silently cut ending.
"""

import math


class AudioVisualTimingGate:
    """Decide whether raw narration can fit the approved visual plan."""

    TOLERANCE_SECONDS = 0.25
    # A narrated episode is not allowed to "finish" with a silent slideshow.
    # One short breath / codec tail is acceptable, but anything longer means
    # Story must add narration or Visual must shorten the approved plan.
    MAX_TRAILING_SILENCE_SECONDS = 0.50
    # A five-second beat remains the authored pacing target.  Measured voice
    # is allowed to keep the same picture alive for a short, intentional
    # camera move/hold through 10 seconds.  This prevents a natural spoken
    # sentence from stopping the whole Studio shift just because it is a
    # little longer than the storyboard estimate.
    MAX_SCENE_SECONDS = 10
    MIN_SCENE_SECONDS = 5
    # A small image hold after the final word makes a cut feel intentional.
    # It is a visual extension, never an instruction to speed up or trim voice.
    END_HOLD_SECONDS = 0.30

    @classmethod
    def plan_scene(cls, audio_seconds, authored_seconds=None):
        """Build the paid-production timeline from the *actual* narration.

        Storyboards retain their five-second authored beat, but rendering is
        allowed to hold the current picture for the narrator's natural cadence
        up to 10 seconds.  A line that cannot fit in that bounded window is
        returned before the remaining scenes are generated; no voice is sped
        up and no completed assets are discarded.
        """
        try:
            audio = float(audio_seconds)
            authored = float(authored_seconds or cls.MIN_SCENE_SECONDS)
        except (TypeError, ValueError):
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["invalid-audio-or-storyboard-duration"],
                "detail": "อ่านความยาวเสียงจริงไม่ได้ จึงยังวาง timeline ฉากนี้ไม่ได้",
            }
        if audio <= 0 or authored <= 0:
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["non-positive-audio-or-storyboard-duration"],
                "detail": "เสียงและจังหวะบทต้องยาวกว่า 0 วินาที",
            }
        required = audio + cls.END_HOLD_SECONDS
        if required > cls.MAX_SCENE_SECONDS:
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["narration-exceeds-safe-scene-window"],
                "audio_seconds": round(audio, 2),
                "maximum_scene_seconds": cls.MAX_SCENE_SECONDS,
                "detail": (
                    f"เสียงฉากนี้ยาว {audio:.2f} วินาที เกินช่วงปลอดภัย {cls.MAX_SCENE_SECONDS} วินาที — "
                    "แยกเป็นสองประโยค/สองฉาก หรือย่อบทก่อนสร้างภาพเพิ่ม"
                ),
            }
        visual = max(cls.MIN_SCENE_SECONDS, authored, required)
        return {
            "eligible": True,
            "state": "pass",
            "reasons": [],
            "audio_seconds": round(audio, 2),
            "visual_seconds": round(visual, 2),
            "hold_seconds": round(visual - audio, 2),
            "action": "extend-current-visual" if visual > authored else "keep-authored-beat",
            "detail": "ใช้เสียงจริงกำหนดความยาวฉาก; ภาพค้างต่ออย่างนุ่มนวลหลังประโยคจบ",
        }

    @classmethod
    def assess(cls, audio_seconds, visual_seconds, max_trailing_silence=None):
        """Return an inspectable pass/return-to-story decision.

        Audio and visual production may proceed in parallel after Story locks
        its timing plan.  Final assembly is allowed only when this gate passes.
        """
        try:
            audio = float(audio_seconds)
            visual = float(visual_seconds)
        except (TypeError, ValueError):
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["invalid-audio-or-storyboard-duration"],
                "detail": "อ่านความยาวเสียงหรือ storyboard ไม่ได้ จึงห้ามประกอบไฟล์สุดท้าย",
            }
        if audio <= 0 or visual <= 0:
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["non-positive-audio-or-storyboard-duration"],
                "audio_seconds": round(audio, 2),
                "visual_seconds": round(visual, 2),
                "detail": "เสียงและ storyboard ต้องมีความยาวมากกว่า 0 วินาทีก่อนผลิต",
            }
        allowed_trailing_silence = (
            cls.MAX_TRAILING_SILENCE_SECONDS
            if max_trailing_silence is None else float(max_trailing_silence)
        )
        delta = audio - visual
        trailing_silence = visual - audio
        eligible = (
            delta <= cls.TOLERANCE_SECONDS
            and trailing_silence <= allowed_trailing_silence
        )
        reasons = []
        if delta > cls.TOLERANCE_SECONDS:
            reasons.append("audio-overruns-storyboard")
        if trailing_silence > allowed_trailing_silence:
            reasons.append("narration-ends-before-final-scene")
        report = {
            "eligible": eligible,
            "state": "pass" if eligible else "return-to-story",
            "reasons": reasons,
            "audio_seconds": round(audio, 2),
            "visual_seconds": round(visual, 2),
            "delta_seconds": round(delta, 2),
        }
        if eligible:
            report["detail"] = "เสียงบรรยายครอบคลุมภาพจนจบ พร้อมประกอบไฟล์สุดท้าย"
        elif delta > cls.TOLERANCE_SECONDS:
            beats = math.ceil(delta / cls.MAX_SCENE_SECONDS)
            report["minimum_extra_visual_beats"] = beats
            report["detail"] = (
                f"เสียงยาวกว่าภาพ {delta:.2f} วินาที — ส่งกลับฝ่ายเรื่องเล่า: "
                f"ย่อบท หรือเพิ่มอย่างน้อย {beats} จังหวะภาพ (จังหวะละไม่เกิน 5 วินาที)"
            )
        else:
            report["trailing_silence_seconds"] = round(trailing_silence, 2)
            report["detail"] = (
                f"เสียงจบก่อนภาพ {trailing_silence:.2f} วินาที — ห้ามประกอบคลิป: "
                "ฝ่ายเรื่องเล่าต้องเติมบทให้ครอบคลุมฉากท้าย หรือฝ่ายภาพต้องลดจำนวนฉาก"
            )
        return report
